"""Persistent per-operator selection for the Feishu single-chat workflow."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .reply_task import ReplyTask, ReplyTaskStatus


@dataclass(slots=True)
class OperatorSelection:
    user_open_id: str
    active_task_id: str | None = None
    updated_at: str | None = None


@dataclass(slots=True)
class OperatorStateStore:
    path: Path
    selections: dict[str, OperatorSelection] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "OperatorStateStore":
        state_path = Path(path)
        if not state_path.exists():
            return cls(state_path)
        raw = json.loads(state_path.read_text(encoding="utf-8"))
        records = raw.get("operators", {}) if isinstance(raw, dict) else {}
        selections = {
            str(user_id): OperatorSelection(
                user_open_id=str(user_id),
                active_task_id=(str(record["active_task_id"]) if record.get("active_task_id") else None),
                updated_at=(str(record["updated_at"]) if record.get("updated_at") else None),
            )
            for user_id, record in records.items()
            if isinstance(record, dict)
        }
        return cls(state_path, selections)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "operators": {
                user_id: {
                    "user_open_id": selection.user_open_id,
                    "active_task_id": selection.active_task_id,
                    "updated_at": selection.updated_at,
                }
                for user_id, selection in sorted(self.selections.items())
            },
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def get(self, user_open_id: str) -> OperatorSelection | None:
        return self.selections.get(user_open_id)

    def set_active(self, user_open_id: str, task_id: str | None) -> OperatorSelection:
        selection = OperatorSelection(
            user_open_id=user_open_id,
            active_task_id=task_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self.selections[user_open_id] = selection
        self.save()
        return selection


def select_next_review_task(
    tasks: Iterable[ReplyTask],
    user_open_id: str,
    state: OperatorStateStore,
) -> ReplyTask | None:
    """Select and persist the earliest reviewable task for one operator."""
    candidates = [
        task
        for task in tasks
        if task.status is ReplyTaskStatus.AWAITING_REVIEW
        and (not task.user_open_id or task.user_open_id == user_open_id)
    ]
    candidates.sort(key=lambda task: (task.created_at or task.updated_at or "", task.reply_task_id))
    task = candidates[0] if candidates else None
    state.set_active(user_open_id, task.reply_task_id if task else None)
    return task


def active_task_for(
    tasks: Iterable[ReplyTask],
    user_open_id: str,
    state: OperatorStateStore,
) -> ReplyTask | None:
    """Return the selected task only while it remains actionable."""
    selection = state.get(user_open_id)
    if selection is None or not selection.active_task_id:
        return None
    task = next((item for item in tasks if item.reply_task_id == selection.active_task_id), None)
    if task is None or task.status in {
        ReplyTaskStatus.SENT,
        ReplyTaskStatus.SKIPPED,
        ReplyTaskStatus.UNKNOWN,
    }:
        return None
    return task


MENU_EVENT_KEYS = {
    "review_next": "review_next",
    "review_list": "review_list",
    "action_send": "action_send",
    "action_rewrite": "action_rewrite",
    "action_skip": "action_skip",
    "system_health": "system_health",
}
