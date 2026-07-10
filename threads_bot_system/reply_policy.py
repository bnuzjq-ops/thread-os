"""Minimal comment triage policy for the reply workflow."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ReplyRoute(str, Enum):
    """Canonical first-pass route for a comment."""

    LIKE_ONLY = "like_only"
    REVIEW = "review"


@dataclass(frozen=True, slots=True)
class ReplyDecision:
    """Output of the first-pass reply triage."""

    route: ReplyRoute
    reason: str


@dataclass(frozen=True, slots=True)
class ReplyPlan:
    """Minimal execution plan derived from a reply decision."""

    decision: ReplyDecision
    should_like: bool
    needs_review: bool


_LOW_SIGNAL_TEXTS = {
    "666",
    "哈哈",
    "哈哈哈",
    "haha",
    "hahaha",
    "nice",
    "good",
    "ok",
    "ok!",
    "赞",
    "支持",
    "顶",
    "路过",
    "牛",
    "厉害",
}


def classify_comment(text: str) -> ReplyDecision:
    """Classify a comment into like-only or review."""
    cleaned = text.strip()
    if not cleaned:
        return ReplyDecision(route=ReplyRoute.LIKE_ONLY, reason="empty_comment")

    compact = "".join(cleaned.split()).casefold()
    if compact in _LOW_SIGNAL_TEXTS:
        return ReplyDecision(route=ReplyRoute.LIKE_ONLY, reason="low_signal_comment")

    if not _has_meaningful_content(compact):
        return ReplyDecision(route=ReplyRoute.LIKE_ONLY, reason="low_signal_comment")

    return ReplyDecision(route=ReplyRoute.REVIEW, reason="needs_review")


def build_reply_plan(text: str) -> ReplyPlan:
    """Build the next-step plan for a comment."""
    decision = classify_comment(text)
    if decision.route is ReplyRoute.LIKE_ONLY:
        return ReplyPlan(decision=decision, should_like=True, needs_review=False)
    return ReplyPlan(decision=decision, should_like=False, needs_review=True)


def _has_meaningful_content(text: str) -> bool:
    for char in text:
        if char.isalnum():
            return True
        if "\u4e00" <= char <= "\u9fff":
            return True
    return False
