"""Build Feishu-ready review card payloads."""

from __future__ import annotations

from dataclasses import dataclass

from .reply_review import ReplyReviewPacket


@dataclass(frozen=True, slots=True)
class ReplyCardAction:
    """A single card action."""

    label: str
    value: str


@dataclass(frozen=True, slots=True)
class ReplyCardPayload:
    """Transport-agnostic representation of a review card."""

    title: str
    body: str
    actions: list[ReplyCardAction]
    draft_version: int | None = None


def build_reply_card(
    packet: ReplyReviewPacket | None,
    draft_version: int | None = None,
) -> ReplyCardPayload | None:
    """Build a card payload from a review packet."""
    if packet is None:
        return None

    actions = [
        ReplyCardAction(label="发送", value=f"send:{packet.task_id}"),
        ReplyCardAction(label="重写", value=f"rewrite:{packet.task_id}"),
        ReplyCardAction(label="跳过", value=f"skip:{packet.task_id}"),
        ReplyCardAction(label="状态", value=f"status:{packet.task_id}"),
    ]
    return ReplyCardPayload(
        title=packet.title,
        body=packet.body,
        actions=actions,
        draft_version=draft_version,
    )
