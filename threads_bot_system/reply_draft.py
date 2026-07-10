"""Conservative draft generation for reply review."""

from __future__ import annotations

from dataclasses import dataclass

from .reply_flow import ReplyIntake
from .reply_policy import ReplyRoute


@dataclass(frozen=True, slots=True)
class ReplyDraft:
    """A conservative reply draft for human review."""

    comment_id: str
    text: str
    version: int = 1


def build_reply_draft(intake: ReplyIntake) -> ReplyDraft | None:
    """Build a human-reviewable draft when the comment needs a reply."""
    if intake.decision.route is ReplyRoute.LIKE_ONLY:
        return None

    text = _build_conservative_draft_text(intake.text)
    return ReplyDraft(comment_id=intake.comment_id, text=text, version=1)


def _build_conservative_draft_text(comment_text: str) -> str:
    cleaned = " ".join(comment_text.split())
    return "\n".join(
        [
            "谢谢你的问题，我先补充一下这个点：",
            cleaned,
        ]
    )
