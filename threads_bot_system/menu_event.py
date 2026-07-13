"""Normalize Feishu bot menu events for the reply operator CLI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from uuid import uuid4


MENU_EVENT_KEYS = {
    "review_next",
    "review_list",
    "action_send",
    "action_rewrite",
    "action_skip",
    "system_health",
}


@dataclass(frozen=True, slots=True)
class MenuEvent:
    event_key: str
    user_open_id: str
    trace_id: str
    raw: Mapping[str, object]


def parse_menu_event(payload: Mapping[str, object]) -> MenuEvent:
    """Extract the stable menu contract from Feishu event variants."""
    event_key = _first_text(
        payload.get("event_key"),
        payload.get("key"),
        _nested(payload, "event", "event_key"),
        _nested(payload, "event", "action", "value"),
        _nested(payload, "action", "value"),
        _nested(payload, "value", "event_key"),
    )
    if event_key not in MENU_EVENT_KEYS:
        raise ValueError(f"Unsupported Feishu menu event: {event_key or '<missing>'}")

    user_open_id = _first_text(
        payload.get("open_id"),
        payload.get("user_open_id"),
        _nested(payload, "event", "sender", "sender_id", "open_id"),
        _nested(payload, "event", "operator", "open_id"),
        _nested(payload, "event", "operator", "operator_id", "open_id"),
        _nested(payload, "sender", "sender_id", "open_id"),
    )
    if not user_open_id:
        raise ValueError("Feishu menu event is missing operator open_id")

    trace_id = _first_text(
        payload.get("trace_id"),
        payload.get("request_id"),
        _nested(payload, "header", "event_id"),
        _nested(payload, "event", "event_id"),
    ) or f"menu-{uuid4().hex}"
    return MenuEvent(event_key, user_open_id, trace_id, payload)


def _nested(value: object, *keys: str) -> object | None:
    current = value
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _first_text(*values: object) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None
