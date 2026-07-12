"""Serialization helpers for publish tasks."""

from __future__ import annotations

from collections.abc import Mapping

from .publish_task import PublishTask, PublishTaskStatus


def task_to_record(task: PublishTask) -> dict[str, object]:
    """Convert a publish task into a JSON-safe record."""
    return {
        "publish_task_id": task.publish_task_id,
        "source_key": task.source_key,
        "text": task.text,
        "status": task.status.value,
        "post_id": task.post_id,
        "platform_post_id": task.post_id,
        "permalink": task.permalink,
        "scheduled_time": task.scheduled_time,
        "error_type": task.error_type,
        "error_phase": task.error_phase,
        "external_action": task.external_action,
        "retry_allowed": task.retry_allowed,
        "recovery_action": task.recovery_action,
        "claimed_at": task.claimed_at,
        "last_error": task.last_error,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def task_from_record(record: Mapping[str, object]) -> PublishTask:
    """Restore a publish task from a persisted record."""
    return PublishTask(
        publish_task_id=str(record["publish_task_id"]),
        source_key=str(record.get("source_key", "")),
        text=str(record.get("text", "")),
        status=_parse_status(record.get("status")),
        post_id=_optional_text(record.get("post_id", record.get("platform_post_id"))),
        permalink=_optional_text(record.get("permalink")),
        scheduled_time=_optional_text(record.get("scheduled_time")),
        error_type=_optional_text(record.get("error_type")),
        error_phase=_optional_text(record.get("error_phase")),
        external_action=bool(record.get("external_action", False)),
        retry_allowed=bool(record.get("retry_allowed", False)),
        recovery_action=_optional_text(record.get("recovery_action")),
        claimed_at=_optional_text(record.get("claimed_at")),
        last_error=_optional_text(record.get("last_error")),
        created_at=_optional_text(record.get("created_at")),
        updated_at=_optional_text(record.get("updated_at")),
    )


def _parse_status(value: object) -> PublishTaskStatus:
    if isinstance(value, PublishTaskStatus):
        return value
    if value is None:
        return PublishTaskStatus.UNKNOWN
    try:
        normalized = str(value)
        if normalized == "pending":
            normalized = PublishTaskStatus.READY.value
        return PublishTaskStatus(normalized)
    except ValueError:
        return PublishTaskStatus.UNKNOWN


def _optional_text(value: object) -> str | None:
    if value is None or value == "":
        return None
    return str(value)
