"""HTTP client for the Cloudflare State Worker task store."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen

from .reply_state import task_from_record
from .reply_task import ReplyTask
from .task_store import TaskClaimResult, TaskCreateResult, TaskStore


class StateApiTaskStoreError(RuntimeError):
    """Raised when the State API task store returns a failure."""


@dataclass(slots=True)
class StateApiTaskStore:
    """A TaskStore implementation backed by the State Worker HTTP API."""

    base_url: str
    api_token: str
    request_impl: Callable[[Request], object] = urlopen

    def create_task(self, comment_id: str, media_id: str = "") -> TaskCreateResult:
        payload = self._request_json(
            "POST",
            "/v1/reply-tasks",
            {
                "comment_id": comment_id,
                "media_id": media_id,
            },
        )
        return TaskCreateResult(
            ok=bool(payload.get("ok", False)),
            created=bool(payload.get("created", False)),
            already_exists=bool(payload.get("already_exists", False)),
            task=self._task_from_payload(payload),
        )

    def get_task(self, task_id: str) -> ReplyTask | None:
        try:
            payload = self._request_json("GET", f"/v1/reply-tasks/{task_id}")
        except StateApiTaskStoreError as exc:
            if "HTTP 404" in str(exc):
                return None
            raise
        task_payload = payload.get("task")
        if not isinstance(task_payload, dict):
            return None
        return self._task_from_record(task_payload)

    def save_draft(self, task_id: str, draft: str) -> ReplyTask:
        payload = self._request_json(
            "POST",
            f"/v1/reply-tasks/{task_id}/draft",
            {"draft": draft},
        )
        return self._task_from_payload(payload)

    def save_feishu_message(self, task_id: str, feishu_message_id: str) -> ReplyTask:
        payload = self._request_json(
            "POST",
            f"/v1/reply-tasks/{task_id}/feishu-message",
            {"feishu_message_id": feishu_message_id},
        )
        return self._task_from_payload(payload)

    def claim_send(self, task_id: str, draft_version: int) -> TaskClaimResult:
        payload = self._request_json(
            "POST",
            f"/v1/reply-tasks/{task_id}/claim-send",
            {"draft_version": draft_version},
        )
        task_payload = payload.get("task")
        task = self._task_from_record(task_payload) if isinstance(task_payload, dict) else None
        return TaskClaimResult(
            ok=bool(payload.get("ok", False)),
            claimed=bool(payload.get("claimed", False)),
            reason=self._optional_text(payload.get("reason")),
            task=task,
        )

    def complete_send(self, task_id: str, reply_id: str) -> ReplyTask:
        payload = self._request_json(
            "POST",
            f"/v1/reply-tasks/{task_id}/complete",
            {"reply_id": reply_id},
        )
        return self._task_from_payload(payload)

    def fail_task(self, task_id: str, error: str) -> ReplyTask:
        payload = self._request_json(
            "POST",
            f"/v1/reply-tasks/{task_id}/fail",
            {"error": error},
        )
        return self._task_from_payload(payload)

    def mark_unknown(self, task_id: str, error: str) -> ReplyTask:
        payload = self._request_json(
            "POST",
            f"/v1/reply-tasks/{task_id}/unknown",
            {"error": error},
        )
        return self._task_from_payload(payload)

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        url = f"{self.base_url.rstrip('/')}{path}"
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
            },
            method=method,
        )
        try:
            response = self.request_impl(request)
            raw_body = response.read()
            status = getattr(response, "status", 200)
        except Exception as exc:  # pragma: no cover - wrapped by caller
            raise StateApiTaskStoreError(f"State API request failed: {exc}") from exc

        body_text = raw_body.decode("utf-8") if isinstance(raw_body, bytes) else str(raw_body)
        try:
            response_payload = json.loads(body_text or "{}")
        except json.JSONDecodeError as exc:
            raise StateApiTaskStoreError("State API response was not valid JSON") from exc

        if status >= 400:
            raise StateApiTaskStoreError(f"State API returned HTTP {status}: {body_text}".rstrip())

        if isinstance(response_payload, dict) and response_payload.get("ok") is False and response_payload.get("claimed") is False:
            return response_payload

        if not isinstance(response_payload, dict):
            raise StateApiTaskStoreError("State API response payload was not an object")

        return response_payload

    def _task_from_payload(self, payload: dict[str, object]) -> ReplyTask:
        task_payload = payload.get("task")
        if not isinstance(task_payload, dict):
            raise StateApiTaskStoreError("State API response did not include a task")
        return self._task_from_record(task_payload)

    def _task_from_record(self, record: dict[str, object]) -> ReplyTask:
        return task_from_record(record)

    @staticmethod
    def _optional_text(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
