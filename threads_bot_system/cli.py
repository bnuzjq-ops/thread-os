"""Command-line entrypoints for the Threads automation system."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Mapping, Sequence

from .contract import render_project_summary
from .deepseek_api import DeepSeekClient
from .export_feed import ensure_feed_repo_clean, export_content, push_export
from .feishu_api import FeishuClient
from .publish_feed import select_manual_source, select_scheduled_source
from .publish_runtime import run_publish
from .publish_source import load_publish_source
from .publish_store import JsonPublishStore
from .reply_runtime import execute_reply_dispatch, run_reply_monitor
from .reply_state import task_to_record
from .threads_api import ThreadsApiClient


DEFAULT_STATE_PATH = Path("state/reply_tasks.json")
DEFAULT_PUBLISH_STATE_PATH = Path("state/publish_tasks.json")
DEFAULT_READY_ROOT = Path(r"C:\jq\OBS\30-Content\Threads\Ready")


def main(argv: Sequence[str] | None = None) -> int:
    """Run a CLI command for the project."""
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    command = args.command or "summary"

    try:
        if command == "summary":
            print(render_project_summary())
            return 0
        if command == "dispatch":
            return _run_dispatch(Path(args.store_path))
        if command == "monitor":
            return _run_monitor(Path(args.store_path), list(args.media_id))
        if command == "publish":
            return _run_publish(
                Path(args.store_path),
                source_path=args.source,
                feed_dir=args.feed_dir,
                content_id=args.content_id,
                scheduled=args.scheduled,
                dry_run=args.dry_run,
            )
        if command == "export-content":
            return _run_export_content(
                source_path=Path(args.source),
                ready_root=Path(args.ready_root),
                feed_repo=Path(args.feed_repo),
                replace=args.replace,
                push=args.push,
            )
        parser.error(f"Unsupported command: {command}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="threads_bot_system")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("summary", help="Print the project summary")

    dispatch = subparsers.add_parser("dispatch", help="Execute a reply action from GitHub")
    dispatch.add_argument(
        "--store-path",
        default=_env("THREADS_STORE_PATH", str(DEFAULT_STATE_PATH)),
        help="Path to the reply task store",
    )

    monitor = subparsers.add_parser(
        "monitor",
        help="Scan replies for the user's Threads posts and build review cards",
    )
    monitor.add_argument(
        "--store-path",
        default=_env("THREADS_STORE_PATH", str(DEFAULT_STATE_PATH)),
        help="Path to the reply task store",
    )
    monitor.add_argument(
        "--media-id",
        action="append",
        default=[],
        help="Threads media id to scan; may be repeated",
    )

    publish = subparsers.add_parser("publish", help="Publish pending Threads posts")
    publish.add_argument(
        "--store-path",
        default=_env("THREADS_PUBLISH_STORE_PATH", str(DEFAULT_PUBLISH_STATE_PATH)),
        help="Path to the publish task store",
    )
    publish.add_argument(
        "--source",
        help="Markdown source to add to the publish task store before publishing",
    )
    publish.add_argument(
        "--feed-dir",
        help="Read-only path to the publish feed posts/queue directory",
    )
    publish.add_argument("--content-id", help="Explicit content id for manual publishing")
    publish.add_argument(
        "--scheduled",
        action="store_true",
        help="Select at most one due scheduled snapshot",
    )
    publish.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report the selected snapshot without writing state or calling Threads",
    )

    export = subparsers.add_parser(
        "export-content",
        help="Export one explicitly selected Obsidian Ready document into the publish feed",
    )
    export.add_argument("--source", required=True, help="Explicit Ready Markdown source")
    export.add_argument(
        "--ready-root",
        default=str(DEFAULT_READY_ROOT),
        help="Allowed Threads Ready directory",
    )
    export.add_argument("--feed-repo", required=True, help="Local publish feed repository")
    export.add_argument("--replace", action="store_true", help="Replace an unpublished snapshot")
    export.add_argument("--push", action="store_true", help="Commit and push only this export")

    return parser


def _run_dispatch(store_path: Path) -> int:
    payload = _load_client_payload(os.environ)
    threads_client = _build_threads_client(os.environ)
    feishu_client = _build_feishu_client(os.environ)
    task = execute_reply_dispatch(payload, threads_client, store_path, feishu_client=feishu_client)
    print(json.dumps(task_to_record(task), ensure_ascii=False, indent=2))
    return 0


def _run_monitor(store_path: Path, media_ids: list[str]) -> int:
    threads_client = _build_threads_client(os.environ)
    resolved_media_ids = [str(media_id).strip() for media_id in media_ids if str(media_id).strip()]
    if not resolved_media_ids:
        resolved_media_ids = threads_client.fetch_user_threads()

    if not resolved_media_ids:
        raise ValueError("No Threads posts found for the current user")

    feishu_client = _build_feishu_client(os.environ)
    deepseek_client = _build_deepseek_client(os.environ)
    report = run_reply_monitor(
        resolved_media_ids,
        threads_client,
        feishu_client,
        store_path,
        deepseek_client=deepseek_client,
    )

    print(
        json.dumps(
            {
                "comments": len(report.comments),
                "like_only_count": report.like_only_count,
                "review_count": report.review_count,
                "store_path": str(store_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _run_publish(
    store_path: Path,
    source_path: str | None = None,
    *,
    feed_dir: str | None = None,
    content_id: str | None = None,
    scheduled: bool = False,
    dry_run: bool = False,
) -> int:
    if source_path and feed_dir:
        raise ValueError("Use either --source or --feed-dir, not both")
    if scheduled and content_id:
        raise ValueError("Scheduled publishing does not accept --content-id")

    source = None
    if feed_dir:
        if scheduled:
            source = select_scheduled_source(feed_dir)
        else:
            if not content_id:
                raise ValueError("Manual feed publishing requires --content-id")
            source = select_manual_source(feed_dir, content_id)
    elif source_path:
        source = load_publish_source(source_path)

    if dry_run:
        if source is None:
            payload = {"selected": False, "reason": "no_eligible_content"}
        else:
            payload = {
                "selected": True,
                "content_id": source.content_id,
                "scheduled_time": source.scheduled_time,
                "content_version": source.content_version,
            }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if feed_dir and source is None:
        print(json.dumps({"selected": False, "reason": "no_eligible_content"}, indent=2))
        return 0

    store = JsonPublishStore.load(store_path)
    selected_task_ids = None
    if source is not None:
        created = store.create_task(source.content_id, source.text)
        selected_task_ids = [created.task.publish_task_id]

    threads_client = _build_threads_client(os.environ)
    if selected_task_ids is None:
        report = run_publish(store, threads_client)
    else:
        report = run_publish(store, threads_client, selected_task_ids)
    print(
        json.dumps(
            {
                "attempted": report.attempted,
                "posted": report.posted,
                "store_path": str(store_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _run_export_content(
    *,
    source_path: Path,
    ready_root: Path,
    feed_repo: Path,
    replace: bool,
    push: bool,
) -> int:
    if push:
        ensure_feed_repo_clean(feed_repo)
    result = export_content(
        source_path,
        feed_repo,
        ready_root=ready_root,
        replace=replace,
    )
    if push:
        push_export(feed_repo, result)
    print(
        json.dumps(
            {
                "content_id": result.content_id,
                "content_version": result.content_version,
                "target_path": str(result.target_path),
                "pushed": push,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _load_client_payload(env: Mapping[str, str]) -> dict[str, object]:
    raw = _env("CLIENT_PAYLOAD_JSON", env=env).strip()
    if raw:
        payload = json.loads(raw)
    else:
        event_path = _env("GITHUB_EVENT_PATH", env=env).strip()
        if not event_path:
            raise ValueError("Missing CLIENT_PAYLOAD_JSON or GITHUB_EVENT_PATH")
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        payload = event.get("client_payload", event)

    if isinstance(payload, dict):
        return payload
    raise ValueError("Client payload must be a JSON object")


def _build_threads_client(env: Mapping[str, str]) -> ThreadsApiClient:
    return ThreadsApiClient(
        user_id=_required_env("THREADS_USER_ID", env),
        access_token=_required_env("THREADS_ACCESS_TOKEN", env),
        base_url=_env("THREADS_API_BASE_URL", "https://graph.threads.net/v1.0", env=env).strip()
        or "https://graph.threads.net/v1.0",
    )


def _build_feishu_client(env: Mapping[str, str]) -> FeishuClient:
    return FeishuClient(
        app_id=_required_env("FEISHU_APP_ID", env),
        app_secret=_required_env("FEISHU_APP_SECRET", env),
        chat_id=_required_env("FEISHU_CHAT_ID", env),
        base_url=_env("FEISHU_API_BASE_URL", "https://open.feishu.cn/open-apis", env=env).strip()
        or "https://open.feishu.cn/open-apis",
    )


def _build_deepseek_client(env: Mapping[str, str]) -> DeepSeekClient | None:
    api_key = _env("DEEPSEEK_API_KEY", env=env).strip()
    if not api_key:
        return None

    return DeepSeekClient(
        api_key=api_key,
        model=_env("DEEPSEEK_MODEL", "deepseek-v4-flash", env=env).strip()
        or "deepseek-v4-flash",
        base_url=_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com", env=env).strip()
        or "https://api.deepseek.com",
    )


def _required_env(name: str, env: Mapping[str, str]) -> str:
    value = _env(name, env=env).strip()
    if not value:
        raise ValueError(f"Missing {name}")
    return value


def _env(name: str, default: str = "", env: Mapping[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    return source.get(name, default)
