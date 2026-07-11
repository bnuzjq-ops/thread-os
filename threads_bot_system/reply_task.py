"""Minimal reply task state model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ReplyTaskStatus(str, Enum):
    """Task states used by the reply workflow."""

    DETECTED = "detected"
    DRAFTED = "drafted"
    AWAITING_REVIEW = "awaiting_review"
    SENDING = "sending"
    SENT = "sent"
    SKIPPED = "skipped"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class ReplyTask:
    """Canonical in-memory reply task record."""

    reply_task_id: str
    comment_id: str
    status: ReplyTaskStatus
    media_id: str = ""
    draft: str = ""
    draft_version: int = 0
    draft_source: str = ""
    feishu_message_id: str | None = None
    reply_id: str | None = None
    claimed_at: str | None = None
    lease_until: str | None = None
    claimed_by: str | None = None
    last_error: str | None = None
    requires_manual_check: bool = False
    created_at: str | None = None
    updated_at: str | None = None


def reply_task_id_for(comment_id: str) -> str:
    """Derive a stable task identifier from the comment id."""
    return f"reply:{comment_id}"


def new_reply_task(comment_id: str, media_id: str = "") -> ReplyTask:
    """Create a fresh reply task record."""
    return ReplyTask(
        reply_task_id=reply_task_id_for(comment_id),
        comment_id=comment_id,
        status=ReplyTaskStatus.DETECTED,
        media_id=media_id,
    )
