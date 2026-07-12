"""Persist the latest Threads comment timestamp seen by the monitor."""

from __future__ import annotations

import json
from pathlib import Path


def load_cursor(path: str | Path) -> str | None:
    cursor_path = Path(path)
    if not cursor_path.exists():
        return None

    payload = json.loads(cursor_path.read_text(encoding="utf-8"))
    timestamp = payload.get("last_seen_timestamp") if isinstance(payload, dict) else None
    if timestamp is None:
        return None
    text = str(timestamp).strip()
    return text or None


def save_cursor(path: str | Path, timestamp: str) -> None:
    cursor_path = Path(path)
    cursor_path.parent.mkdir(parents=True, exist_ok=True)
    cursor_path.write_text(
        json.dumps({"last_seen_timestamp": timestamp}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
