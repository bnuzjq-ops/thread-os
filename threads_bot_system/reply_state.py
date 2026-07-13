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
        "media_id": task.media_id,
        "draft": task.draft,
        "draft_version": task.draft_version,
        "draft_source": task.draft_source,
        "feishu_message_id": task.feishu_message_id,
        "reply_id": task.reply_id,
        "dry_run": task.dry_run,
        "claimed_at": task.claimed_at,
        "lease_until": task.lease_until,
        "claimed_by": task.claimed_by,
        "last_error": task.last_error,
        "requires_manual_check": task.requires_manual_check,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def task_from_record(record: Mapping[str, object]) -> ReplyTask:
    """Restore a reply task from a persisted record."""
    return ReplyTask(
        reply_task_id=str(record["reply_task_id"]),
        comment_id=str(record["comment_id"]),
        status=_parse_status(record.get("status")),
        media_id=str(record.get("media_id", "")),
        draft=str(record.get("draft", "")),
        draft_version=int(record.get("draft_version", 0)),
        draft_source=str(record.get("draft_source", "")),
        feishu_message_id=_optional_text(record.get("feishu_message_id")),
        reply_id=_optional_text(record.get("reply_id")),
        dry_run=bool(record.get("dry_run", False)),
        claimed_at=_optional_text(record.get("claimed_at")),
        lease_until=_optional_text(record.get("lease_until")),
        claimed_by=_optional_text(record.get("claimed_by")),
        last_error=_optional_text(record.get("last_error")),
        requires_manual_check=_optional_bool(record.get("requires_manual_check")),
        created_at=_optional_text(record.get("created_at")),
        updated_at=_optional_text(record.get("updated_at")),
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


def _optional_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "on"}
