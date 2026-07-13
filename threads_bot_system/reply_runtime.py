"""Operational helpers for reply monitoring and reply dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .feishu_api import FeishuClient
from .reply_action import (
    mark_drafted,
    mark_rewrite_requested,
    mark_skipped,
)
from .reply_cursor import load_cursor, save_cursor
from .reply_card import build_reply_card
from .reply_draft import build_reply_draft
from .reply_flow import ReplyIntake, prepare_reply_intake
from .reply_monitor import CommentSnapshot, ReplyMonitorReport, scan_comments
from .reply_review import ReplyReviewPacket, build_reply_review_packet
from .reply_task import ReplyTask, ReplyTaskStatus
from .task_store import JsonTaskStore, TaskStore
from .deepseek_api import DeepSeekClient
from .threads_api import ThreadsApiClient, ThreadsComment


@dataclass(frozen=True, slots=True)
class PlannedReviewTask:
    """A review task prepared from a comment intake."""

    intake: ReplyIntake
    task: ReplyTask
    draft_text: str
    packet: ReplyReviewPacket


def _resolve_task_store(store: TaskStore | str | Path) -> TaskStore:
    if isinstance(store, (str, Path)):
        return JsonTaskStore.load(store)
    return store


def _persist_local_task_update(store: TaskStore, task: ReplyTask) -> ReplyTask:
    if hasattr(store, "upsert") and hasattr(store, "save"):
        store.upsert(task)  # type: ignore[attr-defined]
        store.save()  # type: ignore[attr-defined]
        return task
    raise ValueError("Unsupported reply action for this task store")


def plan_review_tasks(
    comments: Iterable[CommentSnapshot],
    existing_task_ids: set[str] | None = None,
    deepseek_client: DeepSeekClient | None = None,
) -> list[PlannedReviewTask]:
    """Plan reply review work for a batch of comments."""
    existing_task_ids = existing_task_ids or set()
    report = scan_comments(comments)
    planned: list[PlannedReviewTask] = []

    for intake in report.intakes:
        task = intake.task
        if task is None or task.reply_task_id in existing_task_ids:
            continue

        draft = _build_reply_draft(intake, deepseek_client)
        packet = build_reply_review_packet(intake, draft)
        if draft is None or packet is None:
            continue

        task = mark_drafted(task, draft.text)
        planned.append(
            PlannedReviewTask(
                intake=intake,
                task=task,
                draft_text=draft.text,
                packet=packet,
            )
        )

    return planned


def run_reply_monitor(
    media_ids: Iterable[str],
    threads_client: ThreadsApiClient,
    feishu_client: FeishuClient,
    store_path: TaskStore | str | Path,
    deepseek_client: DeepSeekClient | None = None,
    cursor_path: str | Path | None = None,
    dry_run: bool = False,
    trigger_source: str = "",
) -> ReplyMonitorReport:
    """Fetch comments, build review cards, and persist reply tasks."""
    if deepseek_client is None:
        raise RuntimeError("DeepSeek client is required for reply monitor")
    media_id_list = [str(media_id).strip() for media_id in media_ids if str(media_id).strip()]
    comments: list[CommentSnapshot] = []
    for media_id in media_id_list:
        comments.extend(
            _fetch_comment_snapshots(
                threads_client.fetch_replies(media_id),
                media_id=media_id,
            )
        )

    latest_timestamp = _latest_comment_timestamp(comments)
    if cursor_path is not None:
        cursor = load_cursor(cursor_path)
        if cursor is None:
            comments = []
        else:
            comments = [
                comment
                for comment in comments
                if comment.timestamp and comment.timestamp > cursor
            ]

    replied_comment_ids = {
        reply.reply_to_id
        for reply in threads_client.fetch_user_replies()
        if reply.reply_to_id
    }
    comments = [comment for comment in comments if comment.comment_id not in replied_comment_ids]

    report = scan_comments(comments, trigger_source=trigger_source)
    store = _resolve_task_store(store_path)
    for intake in report.intakes:
        if intake.task is None:
            continue

        if dry_run:
            created = store.create_task(
                intake.comment_id,
                intake.media_id,
                dry_run=True,
                comment_text=intake.text,
            )
        else:
            created = store.create_task(
                intake.comment_id,
                intake.media_id,
                comment_text=intake.text,
            )
        if _should_skip_monitor_refresh(created.task):
            continue

        try:
            draft = _build_reply_draft(intake, deepseek_client)
        except Exception as exc:
            store.fail_task(created.task.reply_task_id, str(exc))
            continue

        packet = build_reply_review_packet(intake, draft)
        if draft is None or packet is None:
            store.fail_task(created.task.reply_task_id, "Reply draft was not generated")
            continue

        drafted = store.save_draft(created.task.reply_task_id, draft.text)
        card = build_reply_card(packet)
        if card is None:
            continue

        try:
            message_id = feishu_client.send_review_card(card)
        except Exception as exc:
            try:
                store.fail_task(drafted.reply_task_id, str(exc))
            except Exception:
                pass
            continue

        store.save_feishu_message(drafted.reply_task_id, message_id)
    if cursor_path is not None and latest_timestamp:
        save_cursor(cursor_path, latest_timestamp)
    return report


def execute_reply_dispatch(
    client_payload: dict[str, object],
    threads_client: ThreadsApiClient,
    store_path: TaskStore | str | Path,
    feishu_client: FeishuClient | None = None,
    deepseek_client: DeepSeekClient | None = None,
    dry_run: bool = False,
) -> ReplyTask:
    """Execute a repository_dispatch payload produced by the Feishu callback worker."""
    reply_task_id = _required_text(client_payload.get("reply_task_id"), "reply_task_id")
    action = _required_text(client_payload.get("action"), "action")

    store = _resolve_task_store(store_path)
    task = store.get_task(reply_task_id)
    if task is None:
        if action in {"skip", "rewrite", "status"}:
            return _missing_reply_task(reply_task_id, action)
        raise KeyError(f"Reply task not found: {reply_task_id}")

    # The persisted task flag is authoritative so a dry-run cannot be bypassed
    # by omitting or altering the callback payload flag.
    dry_run = dry_run or task.dry_run

    if action == "status":
        return task

    if action == "skip":
        updated = mark_skipped(task, "skip_requested")
        return _persist_local_task_update(store, updated)

    if action == "rewrite":
        if deepseek_client is None:
            raise RuntimeError("DeepSeek client is required for rewrite")
        if not task.comment_text.strip():
            raise ValueError(f"Reply task {reply_task_id} has no stored comment text")
        intake = prepare_reply_intake(
            task.comment_id,
            task.comment_text,
            media_id=task.media_id,
        )
        draft = deepseek_client.generate_reply_draft(intake)
        updated = mark_rewrite_requested(task, "rewrite_requested")
        updated = mark_drafted(updated, draft.text)
        updated = _persist_local_task_update(store, updated)
        if feishu_client is not None:
            packet = build_reply_review_packet(intake, draft)
            card = build_reply_card(packet)
            if card is not None:
                message_id = feishu_client.send_review_card(card)
                updated = store.save_feishu_message(reply_task_id, message_id)
        return updated

    if action != "send":
        raise ValueError(f"Unsupported reply action: {action}")

    if task.status is ReplyTaskStatus.SENT and task.reply_id:
        return task

    if not task.draft.strip():
        raise ValueError(f"Reply task {reply_task_id} does not have a draft")

    claim = store.claim_send(reply_task_id, task.draft_version)
    if not claim.ok or not claim.claimed or claim.task is None:
        return claim.task or task

    if dry_run:
        completed = store.complete_send(reply_task_id, f"dry-run:{reply_task_id}", dry_run=True)
        if feishu_client is not None:
            feishu_client.send_text_message("Dry-run 已完成：未调用 Threads 回复 API。")
        return completed

    try:
        reply_id = threads_client.publish_reply(reply_to_id=claim.task.comment_id, text=claim.task.draft)
    except TimeoutError as exc:
        try:
            store.mark_unknown(reply_task_id, str(exc))
        except Exception:
            pass
        raise
    except Exception as exc:
        try:
            store.fail_task(reply_task_id, str(exc))
        except Exception:
            pass
        raise

    completed = store.complete_send(reply_task_id, reply_id)
    if feishu_client is not None:
        feishu_client.send_text_message(f"Threads 回复已发送：{reply_id}")
    return completed


def materialize_comment_snapshots(
    items: Iterable[ThreadsComment],
    *,
    media_id: str = "",
) -> list[CommentSnapshot]:
    """Convert API comment rows into the monitor snapshot shape."""
    return [
        CommentSnapshot(
            comment_id=item.comment_id,
            text=item.text,
            timestamp=item.timestamp,
            media_id=media_id,
        )
        for item in items
    ]


def _latest_comment_timestamp(comments: Iterable[CommentSnapshot]) -> str | None:
    timestamps = [comment.timestamp for comment in comments if comment.timestamp]
    return max(timestamps) if timestamps else None


def _fetch_comment_snapshots(
    items: Iterable[ThreadsComment],
    *,
    media_id: str = "",
) -> list[CommentSnapshot]:
    return materialize_comment_snapshots(items, media_id=media_id)


def _build_reply_draft(
    intake: ReplyIntake,
    deepseek_client: DeepSeekClient | None,
):
    if deepseek_client is not None:
        return deepseek_client.generate_reply_draft(intake)

    raise RuntimeError("DeepSeek client is not available; cannot generate draft")


def _required_text(value: object, label: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise ValueError(f"Missing {label}")
    return text


def _missing_reply_task(reply_task_id: str, action: str) -> ReplyTask:
    """Return a harmless placeholder for stale cards that no longer map to state."""
    comment_id = _comment_id_from_task_id(reply_task_id)
    status = ReplyTaskStatus.SKIPPED if action == "skip" else ReplyTaskStatus.UNKNOWN
    last_error = f"Reply task not found for action: {action}"
    return ReplyTask(
        reply_task_id=reply_task_id,
        comment_id=comment_id,
        status=status,
        last_error=last_error,
        requires_manual_check=status is ReplyTaskStatus.UNKNOWN,
    )


def _comment_id_from_task_id(reply_task_id: str) -> str:
    """Recover the original comment id from a reply task id when possible."""
    prefix = "reply:"
    if reply_task_id.startswith(prefix):
        return reply_task_id[len(prefix) :]
    return reply_task_id


def _should_skip_monitor_refresh(task: ReplyTask) -> bool:
    """Skip tasks that have already reached a stable review state."""
    return task.status in {
        ReplyTaskStatus.DRAFTED,
        ReplyTaskStatus.AWAITING_REVIEW,
        ReplyTaskStatus.SENDING,
        ReplyTaskStatus.SENT,
        ReplyTaskStatus.SKIPPED,
        ReplyTaskStatus.FAILED,
        ReplyTaskStatus.UNKNOWN,
    }
