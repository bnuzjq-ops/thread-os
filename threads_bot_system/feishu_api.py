"""Feishu message sending helpers for the reply review workflow."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .reply_card import ReplyCardAction, ReplyCardPayload


class FeishuApiError(RuntimeError):
    """Raised when a Feishu API request fails."""


@dataclass(slots=True)
class FeishuClient:
    """Minimal Feishu client for sending interactive review cards."""

    app_id: str
    app_secret: str
    chat_id: str
    base_url: str = "https://open.feishu.cn/open-apis"
    request_impl: Callable[[Request], object] = urlopen
    _tenant_access_token: str | None = None

    def send_review_card(self, payload: ReplyCardPayload) -> str:
        """Send a review card to the configured chat and return its message id."""
        return self.send_interactive_card(self._build_interactive_card(payload))

    def send_text_message(self, text: str) -> str:
        """Send a plain-text result notification to the configured chat."""
        return self._send_message("text", {"text": text})

    def send_interactive_card(self, card: dict[str, object]) -> str:
        """Send an interactive card payload to the configured chat."""
        return self._send_message("interactive", {"card": card})

    def _send_message(self, msg_type: str, content: dict[str, object]) -> str:
        access_token = self.get_tenant_access_token()
        url = f"{self.base_url}/im/v1/messages?receive_id_type=chat_id"
        body = json.dumps(
            {
                "receive_id": self.chat_id,
                "msg_type": msg_type,
                "content": json.dumps(content, ensure_ascii=False),
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        payload = self._request_json(request)
        message_id = self._optional_text(payload.get("data", {}).get("message_id"))
        if message_id:
            return message_id
        message_id = self._optional_text(payload.get("message_id"))
        if message_id:
            return message_id
        raise FeishuApiError("Feishu send response did not include a message id")

    def get_tenant_access_token(self) -> str:
        """Fetch and cache a tenant access token."""
        if self._tenant_access_token:
            return self._tenant_access_token

        url = f"{self.base_url}/auth/v3/tenant_access_token/internal/"
        body = json.dumps(
            {
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = Request(
            url,
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        payload = self._request_json(request)
        token = self._optional_text(payload.get("tenant_access_token"))
        if not token:
            raise FeishuApiError("Feishu token response did not include tenant_access_token")
        self._tenant_access_token = token
        return token

    def _build_interactive_card(self, payload: ReplyCardPayload) -> dict[str, object]:
        actions: list[dict[str, object]] = []
        for action in payload.actions:
            command, reply_task_id = action.value.split(":", 1)
            actions.append(
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": action.label,
                    },
                    "type": "primary" if action.value.startswith("send:") else "default",
                    "value": {
                        "action": command,
                        "reply_task_id": reply_task_id,
                    },
                }
            )

        return {
            "config": {
                "wide_screen_mode": True,
                "enable_forward": True,
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": payload.title,
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": payload.body,
                    },
                },
                {
                    "tag": "action",
                    "actions": actions,
                },
            ],
        }

    def _request_json(self, request: Request) -> dict[str, object]:
        try:
            response = self.request_impl(request)
            raw_body = response.read()
            status = getattr(response, "status", 200)
        except Exception as exc:  # pragma: no cover - wrapped by caller
            raise FeishuApiError(f"Feishu request failed: {exc}") from exc

        body_text = raw_body.decode("utf-8") if isinstance(raw_body, bytes) else str(raw_body)
        try:
            payload = json.loads(body_text or "{}")
        except json.JSONDecodeError as exc:
            raise FeishuApiError("Feishu response was not valid JSON") from exc

        if status >= 400:
            raise FeishuApiError(f"Feishu API returned HTTP {status}: {body_text}".rstrip())

        if isinstance(payload, dict) and payload.get("code") not in (None, 0):
            raise FeishuApiError(str(payload.get("msg") or payload.get("error") or "Feishu API error"))

        if not isinstance(payload, dict):
            raise FeishuApiError("Feishu response payload was not an object")

        return payload

    @staticmethod
    def _optional_text(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
