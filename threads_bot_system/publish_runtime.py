"""Operational helpers for publish automation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import sys
from datetime import datetime, timezone
from typing import Iterable

from .production_guard import ProductionGuardConfig, pre_publish_check
from .publish_store import JsonPublishStore
from .publish_task import PublishTask, PublishTaskStatus
from .threads_api import ThreadsApiClient


@dataclass(frozen=True, slots=True)
class PublishRunReport:
    """Summary of a publish run."""

    attempted: int
    posted: int
    tasks: list[PublishTask]


class PublishRunError(RuntimeError):
    """Raised when the publish workflow cannot produce a successful post."""


def _resolve_publish_store(store: JsonPublishStore | str | Path) -> JsonPublishStore:
    if isinstance(store, (str, Path)):
        return JsonPublishStore.load(store)
    return store


def run_publish(
    store: JsonPublishStore | str | Path,
    threads_client: ThreadsApiClient,
    task_ids: Iterable[str] | None = None,
    *,
    config: ProductionGuardConfig | None = None,
) -> PublishRunReport:
    """Publish pending tasks and persist the result.

    If config is not provided, it is built from os.environ.
    Production safety checks run before any real API call.
    """
    if config is None:
        config = ProductionGuardConfig.from_env(os.environ)

    if not config.is_production:
        # In non-production mode, run as dry-run — log what would happen
        print(
            f"[DRY-RUN] Publish blocked: ENV={config.env}, "
            f"PUBLISH_ENABLED={config.publish_enabled}, DRY_RUN={config.dry_run}",
            file=sys.stderr,
        )
        publish_store = _resolve_publish_store(store)
        selected_task_ids = _normalize_task_ids(task_ids)
        tasks = _select_tasks(publish_store, selected_task_ids)
        for task in tasks:
            print(
                f"[DRY-RUN] Would publish: task_id={task.publish_task_id}, "
                f"text_len={len(task.text)}, "
                f"scheduled={task.scheduled_time or 'immediate'}",
                file=sys.stderr,
            )
        return PublishRunReport(attempted=0, posted=0, tasks=tasks)

    publish_store = _resolve_publish_store(store)
    selected_task_ids = _normalize_task_ids(task_ids)
    tasks = _select_tasks(publish_store, selected_task_ids)
    attempted = 0
    posted = 0
    processed: list[PublishTask] = []

    for task in tasks:
        claim = publish_store.claim_publish(task.publish_task_id)
        if not claim.ok or not claim.claimed or claim.task is None:
            processed.append(claim.task or task)
            continue

        attempted += 1
        try:
            post_id = threads_client.publish_post(text=claim.task.text)
            permalink = None
            metadata_error = None
            get_permalink = getattr(threads_client, "get_post_permalink", None)
            if get_permalink is not None:
                try:
                    permalink = get_permalink(post_id)
                except Exception as exc:
                    metadata_error = f"permalink lookup failed: {exc}"
                    print(
                        f"Permalink lookup failed for {task.publish_task_id}: {exc}",
                        file=sys.stderr,
                    )
        except TimeoutError as exc:
            print(
                f"Publish uncertain for {task.publish_task_id}: {exc}",
                file=sys.stderr,
            )
            try:
                uncertain = publish_store.mark_unknown(task.publish_task_id, str(exc), "threads_publish")
            except Exception:
                uncertain = claim.task
            processed.append(uncertain)
            continue
        except Exception as exc:
            print(
                f"Publish failed for {task.publish_task_id}: {exc}",
                file=sys.stderr,
            )
            try:
                    failed = publish_store.fail_task(
                        task.publish_task_id,
                        str(exc),
                        error_type=_classify_error(exc),
                        error_phase="threads_publish",
                        external_action=False,
                    )
            except Exception:
                failed = claim.task
            processed.append(failed)
            continue

        completed = publish_store.complete_publish(
            task.publish_task_id,
            post_id,
            permalink,
            metadata_error,
        )
        posted += 1
        processed.append(completed)

    if attempted > 0 and posted == 0:
        raise PublishRunError("Publish workflow attempted posts but none succeeded")

    return PublishRunReport(attempted=attempted, posted=posted, tasks=processed)


def _select_tasks(store: JsonPublishStore, task_ids: set[str]) -> list[PublishTask]:
    tasks = [
        task
        for task in store.tasks.values()
        if task.status is PublishTaskStatus.READY and _is_due(task.scheduled_time)
    ]
    tasks.sort(key=lambda item: item.publish_task_id)
    if not task_ids:
        return tasks
    return [task for task in tasks if task.publish_task_id in task_ids]


def _normalize_task_ids(task_ids: Iterable[str] | None) -> set[str]:
    if task_ids is None:
        return set()
    return {str(task_id).strip() for task_id in task_ids if str(task_id).strip()}


def _is_due(value: str | None) -> bool:
    if not value:
        return True
    try:
        scheduled = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if scheduled.tzinfo is None:
        return False
    return scheduled.astimezone(timezone.utc) <= datetime.now(timezone.utc)


def _classify_error(exc: Exception) -> str:
    message = str(exc).lower()
    if isinstance(exc, ValueError):
        return "validation_error"
    if "401" in message or "unauthorized" in message or "token" in message:
        return "authentication_error"
    if "timeout" in message or isinstance(exc, TimeoutError):
        return "network_error"
    return "external_api_error"
