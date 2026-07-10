"""Serialization helpers for reply tasks."""

from __future__ import annotations

from collections.abc import Mapping

from .reply_task import ReplyTask, ReplyTaskStatus


def task_to_record(task: ReplyTask) -> dict[str, object]:
    """Convert a reply task into a JSON-safe record."""
    return {
        "reply_task_id": task.reply_task_id,
        "comment_id": task.comment_id,
        "status": task.status.value,
        "draft": task.draft,
        "draft_version": task.draft_version,
        "feishu_message_id": task.feishu_message_id,
        "reply_id": task.reply_id,
        "last_error": task.last_error,
    }


def task_from_record(record: Mapping[str, object]) -> ReplyTask:
    """Restore a reply task from a persisted record."""
    return ReplyTask(
        reply_task_id=str(record["reply_task_id"]),
        comment_id=str(record["comment_id"]),
        status=_parse_status(record.get("status")),
        draft=str(record.get("draft", "")),
        draft_version=int(record.get("draft_version", 0)),
        feishu_message_id=_optional_text(record.get("feishu_message_id")),
        reply_id=_optional_text(record.get("reply_id")),
        last_error=_optional_text(record.get("last_error")),
    )


def _parse_status(value: object) -> ReplyTaskStatus:
    if isinstance(value, ReplyTaskStatus):
        return value
    if value is None:
        return ReplyTaskStatus.UNKNOWN
    try:
        return ReplyTaskStatus(str(value))
    except ValueError:
        return ReplyTaskStatus.UNKNOWN


def _optional_text(value: object) -> str | None:
    if value is None or value == "":
        return None
    return str(value)
