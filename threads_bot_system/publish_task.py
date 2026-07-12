"""Minimal publish task state model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class PublishTaskStatus(str, Enum):
    """Task states used by the publish workflow."""

    READY = "ready"
    PENDING = "ready"  # Backward-compatible Python name.
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    SKIPPED = "skipped"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class PublishTask:
    """Canonical in-memory publish task record."""

    publish_task_id: str
    source_key: str
    text: str
    status: PublishTaskStatus
    post_id: str | None = None
    permalink: str | None = None
    scheduled_time: str | None = None
    error_type: str | None = None
    claimed_at: str | None = None
    last_error: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


def publish_task_id_for(source_key: str) -> str:
    """Derive a stable task identifier from the source key."""
    return f"publish:{source_key}"


def new_publish_task(
    source_key: str,
    text: str,
    scheduled_time: str | None = None,
) -> PublishTask:
    """Create a fresh publish task record."""
    source_key = source_key.strip()
    if not source_key:
        raise ValueError("source_key is required")

    now = datetime.now(timezone.utc).isoformat()
    return PublishTask(
        publish_task_id=publish_task_id_for(source_key),
        source_key=source_key,
        text=text,
        status=PublishTaskStatus.READY,
        scheduled_time=scheduled_time,
        created_at=now,
        updated_at=now,
    )
