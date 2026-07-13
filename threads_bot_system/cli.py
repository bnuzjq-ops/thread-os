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
from .feishu_api import FeishuClient
from .publish_runtime import run_publish
from .publish_source import load_publish_source, select_due_source
from .publish_store import JsonPublishStore
from .reply_runtime import execute_reply_dispatch, run_reply_monitor
from .reply_state import task_to_record
from .threads_api import ThreadsApiClient


DEFAULT_STATE_PATH = Path("state/reply_tasks.json")
DEFAULT_PUBLISH_STATE_PATH = Path("state/publish_tasks.json")


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
            return _run_monitor(Path(args.store_path), list(args.media_id), Path(args.cursor_path))
        if command == "publish":
            return _run_publish(Path(args.store_path), args.source)
        if command == "select-scheduled-source":
            selected = select_due_source(args.root)
            if selected is not None:
                print(selected)
            return 0
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
    monitor.add_argument(
        "--cursor-path",
        default=_env("THREADS_MONITOR_CURSOR_PATH", "state/reply_monitor_cursor.json"),
        help="Path to the latest-seen comment cursor",
    )

    publish = subparsers.add_parser("publish", help="Publish pending Threads posts")
    publish.add_argument(
        "--store-path",
        default=_env("THREADS_PUBLISH_STORE_PATH", str(DEFAULT_PUBLISH_STATE_PATH)),
        help="Path to the publish task store",
    )

    select = subparsers.add_parser("select-scheduled-source")
    select.add_argument("root", help="Queue directory containing publish snapshots")
    publish.add_argument(
        "--source",
        help="Markdown source to add to the publish task store before publishing",
    )

    return parser


def _run_dispatch(store_path: Path) -> int:
    payload = _load_client_payload(os.environ)
    threads_client = _build_threads_client(os.environ)
    feishu_client = _build_feishu_client(os.environ)
    deepseek_client = _build_deepseek_client(os.environ)
    task = execute_reply_dispatch(
        payload,
        threads_client,
        store_path,
        feishu_client=feishu_client,
        deepseek_client=deepseek_client,
        dry_run=_env("REPLY_DRY_RUN", "0", env=os.environ).lower() in {"1", "true", "yes"},
    )
    print(json.dumps(task_to_record(task), ensure_ascii=False, indent=2))
    return 0


def _run_monitor(store_path: Path, media_ids: list[str], cursor_path: Path) -> int:
    threads_client = _build_threads_client(os.environ)
    resolved_media_ids = [str(media_id).strip() for media_id in media_ids if str(media_id).strip()]
    if not resolved_media_ids:
        resolved_media_ids = threads_client.fetch_user_threads()

    if not resolved_media_ids:
        raise ValueError("No Threads posts found for the current user")

    feishu_client = _build_feishu_client(os.environ)
    deepseek_client = _build_deepseek_client(os.environ)
    monitor_kwargs = {
        "deepseek_client": deepseek_client,
        "cursor_path": cursor_path,
    }
    if _env("REPLY_DRY_RUN", "0", env=os.environ).lower() in {"1", "true", "yes"}:
        monitor_kwargs["dry_run"] = True
    trigger_source = _env("REPLY_TRIGGER_SOURCE", "manual", env=os.environ).strip()
    report = run_reply_monitor(
        resolved_media_ids,
        threads_client,
        feishu_client,
        store_path,
        **monitor_kwargs,
        trigger_source=trigger_source,
    )

    print(
        json.dumps(
            {
                "comments": len(report.comments),
                "like_only_count": report.like_only_count,
                "review_count": report.review_count,
                "trigger_source": report.trigger_source,
                "store_path": str(store_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _run_publish(store_path: Path, source_path: str | None = None) -> int:
    threads_client = _build_threads_client(os.environ)
    store = JsonPublishStore.load(store_path)
    if source_path:
        source = load_publish_source(source_path)
        store.create_task(source.content_id, source.text, source.scheduled_time)
    report = run_publish(store, threads_client)
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
