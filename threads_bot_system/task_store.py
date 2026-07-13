"""Persistence helpers for reply tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Protocol, runtime_checkable

from .reply_action import mark_awaiting_review, mark_drafted, mark_failed, mark_sent, mark_sending
from .reply_state import task_from_record, task_to_record
from .reply_task import ReplyTask, ReplyTaskStatus, new_reply_task, reply_task_id_for


STATE_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class TaskCreateResult:
    """Result of creating or reusing a reply task."""

    ok: bool
    created: bool
    already_exists: bool
    task: ReplyTask


@dataclass(frozen=True, slots=True)
class TaskClaimResult:
    """Result of attempting to claim send authority."""

    ok: bool
    claimed: bool
    reason: str | None
    task: ReplyTask | None


@runtime_checkable
class TaskStore(Protocol):
    """Uniform storage interface for reply tasks."""

    def create_task(self, comment_id: str, media_id: str = "") -> TaskCreateResult:
        """Create a task once per comment id."""

    def get_task(self, task_id: str) -> ReplyTask | None:
        """Return a task by id."""

    def save_draft(self, task_id: str, draft: str) -> ReplyTask:
        """Persist a draft body for a task."""

    def save_feishu_message(self, task_id: str, feishu_message_id: str) -> ReplyTask:
        """Persist the Feishu message id for a task."""

    def claim_send(self, task_id: str, draft_version: int) -> TaskClaimResult:
        """Atomically claim send authority for a task."""

    def complete_send(self, task_id: str, reply_id: str, dry_run: bool = False) -> ReplyTask:
        """Mark a task as sent."""

    def fail_task(self, task_id: str, error: str) -> ReplyTask:
        """Mark a task as failed."""

    def mark_unknown(self, task_id: str, error: str) -> ReplyTask:
        """Mark a task as unknown."""


@dataclass(slots=True)
class JsonTaskStore:
    """A tiny JSON-backed store for reply tasks."""

    path: Path
    tasks: dict[str, ReplyTask] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "JsonTaskStore":
        store_path = Path(path)
        if not store_path.exists():
            return cls(path=store_path)

        raw = json.loads(store_path.read_text(encoding="utf-8"))
        task_records: dict[str, object]
        if isinstance(raw, dict) and isinstance(raw.get("tasks"), dict):
            task_records = raw["tasks"]
        elif isinstance(raw, dict):
            task_records = raw
        elif isinstance(raw, list):
            task_records = {
                str(record["reply_task_id"]): record
                for record in raw
                if isinstance(record, dict) and "reply_task_id" in record
            }
        else:
            task_records = {}

        tasks = {
            reply_task_id: task_from_record(record)
            for reply_task_id, record in task_records.items()
            if isinstance(record, dict)
        }
        return cls(path=store_path, tasks=tasks)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": STATE_SCHEMA_VERSION,
            "tasks": {
                reply_task_id: task_to_record(task)
                for reply_task_id, task in sorted(self.tasks.items())
            },
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def get(self, reply_task_id: str) -> ReplyTask | None:
        return self.tasks.get(reply_task_id)

    def upsert(self, task: ReplyTask) -> None:
        self.tasks[task.reply_task_id] = task

    def create_task(self, comment_id: str, media_id: str = "") -> TaskCreateResult:
        task_id = reply_task_id_for(comment_id)
        existing = self.get(task_id)
        if existing is not None:
            return TaskCreateResult(
                ok=True,
                created=False,
                already_exists=True,
                task=existing,
            )

        task = new_reply_task(comment_id, media_id=media_id)
        self.upsert(task)
        self.save()
        return TaskCreateResult(
            ok=True,
            created=True,
            already_exists=False,
            task=task,
        )

    def get_task(self, task_id: str) -> ReplyTask | None:
        return self.get(task_id)

    def save_draft(self, task_id: str, draft: str) -> ReplyTask:
        task = self._require_task(task_id)
        updated = mark_drafted(task, draft)
        self.upsert(updated)
        self.save()
        return updated

    def save_feishu_message(self, task_id: str, feishu_message_id: str) -> ReplyTask:
        task = self._require_task(task_id)
        updated = mark_awaiting_review(task, feishu_message_id)
        self.upsert(updated)
        self.save()
        return updated

    def claim_send(self, task_id: str, draft_version: int) -> TaskClaimResult:
        task = self._require_task(task_id)
        if task.status is not ReplyTaskStatus.AWAITING_REVIEW or task.draft_version != draft_version:
            return TaskClaimResult(
                ok=False,
                claimed=False,
                reason="already_claimed_or_stale_version",
                task=task,
            )

        updated = mark_sending(task)
        self.upsert(updated)
        self.save()
        return TaskClaimResult(ok=True, claimed=True, reason=None, task=updated)

    def complete_send(self, task_id: str, reply_id: str, dry_run: bool = False) -> ReplyTask:
        task = self._require_task(task_id)
        updated = mark_sent(task, reply_id, dry_run=dry_run)
        self.upsert(updated)
        self.save()
        return updated

    def fail_task(self, task_id: str, error: str) -> ReplyTask:
        task = self._require_task(task_id)
        updated = mark_failed(task, error)
        self.upsert(updated)
        self.save()
        return updated

    def mark_unknown(self, task_id: str, error: str) -> ReplyTask:
        task = self._require_task(task_id)
        updated = replace(task, status=ReplyTaskStatus.UNKNOWN, last_error=error)
        self.upsert(updated)
        self.save()
        return updated

    def _require_task(self, task_id: str) -> ReplyTask:
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"Reply task not found: {task_id}")
        return task


# Backward compatibility for the existing code and tests.
ReplyTaskStore = JsonTaskStore
