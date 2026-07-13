"""Batch comment intake for the reply workflow."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .reply_flow import ReplyIntake, prepare_reply_intake
from .reply_task import ReplyTask


@dataclass(frozen=True, slots=True)
class CommentSnapshot:
    """Minimal comment shape consumed by the monitor."""

    comment_id: str
    text: str
    media_id: str = ""
    timestamp: str | None = None


@dataclass(slots=True)
class ReplyMonitorReport:
    """Aggregated output of a monitoring pass."""

    comments: list[CommentSnapshot]
    intakes: list[ReplyIntake]
    trigger_source: str = ""

    @property
    def like_only_count(self) -> int:

    @property
    def like_only_count(self) -> int:
        return sum(1 for intake in self.intakes if intake.plan.should_like)

    @property
    def review_count(self) -> int:
        return sum(1 for intake in self.intakes if intake.plan.needs_review)

    @property
    def review_tasks(self) -> list[ReplyTask]:
        return [intake.task for intake in self.intakes if intake.task is not None]


def scan_comments(comments: Iterable[CommentSnapshot], *, trigger_source: str = "") -> ReplyMonitorReport:
    """Run the first-pass reply intake over a batch of comments."""
    comment_list = list(comments)
    intakes = [
        prepare_reply_intake(comment.comment_id, comment.text, comment.media_id)
        for comment in comment_list
    ]
    return ReplyMonitorReport(comments=comment_list, intakes=intakes, trigger_source=trigger_source)
