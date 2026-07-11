"""Persistence helpers for publish tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path

from .publish_state import task_from_record, task_to_record
from .publish_task import PublishTask, PublishTaskStatus, new_publish_task, publish_task_id_for


STATE_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class PublishCreateResult:
    """Result of creating or reusing a publish task."""

    ok: bool
    created: bool
    already_exists: bool
    task: PublishTask


@dataclass(frozen=True, slots=True)
class PublishClaimResult:
    """Result of attempting to claim publish authority."""

    ok: bool
    claimed: bool
    reason: str | None
    task: PublishTask | None


@dataclass(slots=True)
class JsonPublishStore:
    """A tiny JSON-backed store for publish tasks."""

    path: Path
    tasks: dict[str, PublishTask] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "JsonPublishStore":
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
                str(record["publish_task_id"]): record
                for record in raw
                if isinstance(record, dict) and "publish_task_id" in record
            }
        else:
            task_records = {}

        tasks = {
            publish_task_id: task_from_record(record)
            for publish_task_id, record in task_records.items()
            if isinstance(record, dict)
        }
        return cls(path=store_path, tasks=tasks)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": STATE_SCHEMA_VERSION,
            "tasks": {
                publish_task_id: task_to_record(task)
                for publish_task_id, task in sorted(self.tasks.items())
            },
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def get(self, publish_task_id: str) -> PublishTask | None:
        return self.tasks.get(publish_task_id)

    def upsert(self, task: PublishTask) -> None:
        self.tasks[task.publish_task_id] = task

    def create_task(self, source_key: str, text: str) -> PublishCreateResult:
        task_id = publish_task_id_for(source_key)
        existing = self.get(task_id)
        if existing is not None:
            return PublishCreateResult(
                ok=True,
                created=False,
                already_exists=True,
                task=existing,
            )

        task = new_publish_task(source_key, text)
        self.upsert(task)
        self.save()
        return PublishCreateResult(
            ok=True,
            created=True,
            already_exists=False,
            task=task,
        )

    def get_task(self, task_id: str) -> PublishTask | None:
        return self.get(task_id)

    def claim_publish(self, task_id: str) -> PublishClaimResult:
        task = self._require_task(task_id)
        if task.status is not PublishTaskStatus.READY:
            return PublishClaimResult(
                ok=False,
                claimed=False,
                reason="already_claimed_or_non_ready",
                task=task,
            )

        updated = replace(task, status=PublishTaskStatus.PUBLISHING, last_error=None)
        self.upsert(updated)
        self.save()
        return PublishClaimResult(ok=True, claimed=True, reason=None, task=updated)

    def complete_publish(self, task_id: str, post_id: str) -> PublishTask:
        task = self._require_task(task_id)
        updated = replace(
            task,
            status=PublishTaskStatus.PUBLISHED,
            post_id=post_id,
            last_error=None,
        )
        self.upsert(updated)
        self.save()
        return updated

    def fail_task(self, task_id: str, error: str) -> PublishTask:
        task = self._require_task(task_id)
        updated = replace(task, status=PublishTaskStatus.FAILED, last_error=error)
        self.upsert(updated)
        self.save()
        return updated

    def mark_unknown(self, task_id: str, error: str) -> PublishTask:
        task = self._require_task(task_id)
        updated = replace(task, status=PublishTaskStatus.UNKNOWN, last_error=error)
        self.upsert(updated)
        self.save()
        return updated

    def _require_task(self, task_id: str) -> PublishTask:
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"Publish task not found: {task_id}")
        return task


# Backward-compatible alias for the JSON implementation.
PublishTaskStore = JsonPublishStore
