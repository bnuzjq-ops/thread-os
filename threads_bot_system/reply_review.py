"""Build human-review packets for the reply workflow."""

from __future__ import annotations

from dataclasses import dataclass

from .reply_draft import ReplyDraft
from .reply_flow import ReplyIntake


@dataclass(frozen=True, slots=True)
class ReplyReviewPacket:
    """Payload presented to a human reviewer."""

    comment_id: str
    task_id: str
    title: str
    body: str


def build_reply_review_packet(
    intake: ReplyIntake,
    draft: ReplyDraft | None,
) -> ReplyReviewPacket | None:
    """Build a review packet only when a reply draft exists."""
    if draft is None or intake.task is None:
        return None

    title = f"回复审核 · {intake.comment_id}"
    body = "\n".join(
        [
            f"评论 ID: {intake.comment_id}",
            "原评论:",
            intake.text,
            "",
            "回复草稿:",
            draft.text,
        ]
    )
    return ReplyReviewPacket(
        comment_id=intake.comment_id,
        task_id=intake.task.reply_task_id,
        title=title,
        body=body,
    )
