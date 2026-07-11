"""Compose the first reply intake result for a comment."""

from __future__ import annotations

from dataclasses import dataclass

from .reply_policy import ReplyDecision, ReplyPlan, ReplyRoute, build_reply_plan, classify_comment
from .reply_task import ReplyTask, new_reply_task


@dataclass(slots=True)
class ReplyIntake:
    """Unified first-pass result for a comment."""

    comment_id: str
    text: str
    media_id: str
    decision: ReplyDecision
    plan: ReplyPlan
    task: ReplyTask | None


def prepare_reply_intake(comment_id: str, text: str, media_id: str = "") -> ReplyIntake:
    """Prepare the reply intake bundle for a comment."""
    decision = classify_comment(text)
    plan = build_reply_plan(text)
    task = new_reply_task(comment_id, media_id=media_id) if decision.route is ReplyRoute.REVIEW else None
    return ReplyIntake(
        comment_id=comment_id,
        text=text,
        media_id=media_id,
        decision=decision,
        plan=plan,
        task=task,
    )
