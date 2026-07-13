"""Pure state transitions for the reply workflow."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from .reply_task import ReplyTask, ReplyTaskStatus


def mark_drafted(task: ReplyTask, draft: str) -> ReplyTask:
    """Record a new draft for a reply task."""
    return replace(
        task,
        status=ReplyTaskStatus.DRAFTED,
        draft=draft,
        draft_version=task.draft_version + 1,
        last_error=None,
    )


def mark_awaiting_review(
    task: ReplyTask,
    feishu_message_id: str,
    draft: str | None = None,
) -> ReplyTask:
    """Move a drafted task into the review queue."""
    return replace(
        task,
        status=ReplyTaskStatus.AWAITING_REVIEW,
        draft=task.draft if draft is None else draft,
        feishu_message_id=feishu_message_id,
        card_sent_at=datetime.now(timezone.utc).isoformat(),
        active_card_version=task.draft_version,
        last_error=None,
    )


def mark_sending(task: ReplyTask) -> ReplyTask:
    """Mark a task as in-flight for sending."""
    return replace(task, status=ReplyTaskStatus.SENDING, last_error=None)


def mark_sent(task: ReplyTask, reply_id: str, dry_run: bool = False) -> ReplyTask:
    """Mark a task as successfully sent."""
    return replace(
        task,
        status=ReplyTaskStatus.SENT,
        reply_id=reply_id,
        dry_run=dry_run,
        last_error="dry_run: Threads reply was not called" if dry_run else None,
    )


def mark_skipped(task: ReplyTask, reason: str) -> ReplyTask:
    """Mark a task as intentionally skipped."""
    return replace(task, status=ReplyTaskStatus.SKIPPED, last_error=reason)


def mark_rewrite_requested(task: ReplyTask, reason: str) -> ReplyTask:
    """Record that a reviewer wants the draft rewritten."""
    return replace(task, status=ReplyTaskStatus.DRAFTED, last_error=reason)


def mark_failed(task: ReplyTask, error: str) -> ReplyTask:
    """Mark a task as failed."""
    return replace(task, status=ReplyTaskStatus.FAILED, last_error=error)
