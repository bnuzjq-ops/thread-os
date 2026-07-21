"""Small Threads API client for reply monitoring and sending."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Callable
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ThreadsApiError(RuntimeError):
    """Raised when the Threads API returns a failure."""


@dataclass(frozen=True, slots=True)
class ThreadsComment:
    """Normalized comment data fetched from Threads."""

    comment_id: str
    text: str
    username: str | None = None
    timestamp: str | None = None
    reply_to_id: str | None = None


@dataclass(frozen=True, slots=True)
class ThreadsReplyPage:
    """A single paginated page of Threads replies."""

    comments: list[ThreadsComment]
    next_after: str | None


@dataclass(frozen=True, slots=True)
class ThreadsMediaPage:
    """A single paginated page of Threads media objects."""

    media_ids: list[str]
    next_after: str | None


@dataclass(slots=True)
class ThreadsApiClient:
    """A tiny HTTP client for the official Threads API."""

    user_id: str
    access_token: str
    base_url: str = "https://graph.threads.net/v1.0"
    request_impl: Callable[[Request], object] = urlopen
    sleep_impl: Callable[[float], None] = time.sleep
    container_poll_attempts: int = 6
    container_poll_seconds: float = 5.0

    def fetch_replies(self, media_id: str, limit: int = 100) -> list[ThreadsComment]:
        comments: list[ThreadsComment] = []
        after: str | None = None

        while True:
            page = self.fetch_replies_page(media_id, limit=limit, after=after)
            comments.extend(page.comments)
            if not page.next_after:
                break
            after = page.next_after

        return comments

    def fetch_user_threads(self, limit: int = 100) -> list[str]:
        media_ids: list[str] = []
        after: str | None = None

        while True:
            page = self.fetch_user_threads_page(limit=limit, after=after)
            media_ids.extend(page.media_ids)
            if not page.next_after:
                break
            after = page.next_after

        return media_ids

    def fetch_user_replies(self, limit: int = 100) -> list[ThreadsComment]:
        comments: list[ThreadsComment] = []
        after: str | None = None

        while True:
            page = self.fetch_user_replies_page(limit=limit, after=after)
            comments.extend(page.comments)
            if not page.next_after:
                break
            after = page.next_after

        return comments

    def fetch_user_threads_page(
        self,
        limit: int = 100,
        after: str | None = None,
    ) -> ThreadsMediaPage:
        params = {
            "access_token": self.access_token,
            "fields": "id",
            "limit": str(limit),
        }
        if after:
            params["after"] = after

        url = f"{self.base_url}/{self.user_id}/threads?{urlencode(params)}"
        payload = self._request_json("GET", url)
        data = payload.get("data", [])
        media_ids = [self._parse_media_id(item) for item in data if isinstance(item, dict)]

        paging = payload.get("paging", {})
        next_after = None
        if isinstance(paging, dict):
            cursors = paging.get("cursors", {})
            if isinstance(cursors, dict):
                next_after = self._optional_text(cursors.get("after"))

        return ThreadsMediaPage(media_ids=media_ids, next_after=next_after)

    def fetch_replies_page(
        self,
        media_id: str,
        limit: int = 100,
        after: str | None = None,
    ) -> ThreadsReplyPage:
        params = {
            "access_token": self.access_token,
            "fields": "id,text,username,timestamp",
            "limit": str(limit),
        }
        if after:
            params["after"] = after

        url = f"{self.base_url}/{media_id}/replies?{urlencode(params)}"
        payload = self._request_json("GET", url)
        data = payload.get("data", [])
        comments = [self._parse_comment(item) for item in data if isinstance(item, dict)]

        paging = payload.get("paging", {})
        next_after = None
        if isinstance(paging, dict):
            cursors = paging.get("cursors", {})
            if isinstance(cursors, dict):
                next_after = self._optional_text(cursors.get("after"))

        return ThreadsReplyPage(comments=comments, next_after=next_after)

    def fetch_user_replies_page(
        self,
        limit: int = 100,
        after: str | None = None,
    ) -> ThreadsReplyPage:
        params = {
            "access_token": self.access_token,
            "fields": "id,text,username,timestamp,reply_to_id",
            "limit": str(limit),
        }
        if after:
            params["after"] = after

        url = f"{self.base_url}/{self.user_id}/replies?{urlencode(params)}"
        payload = self._request_json("GET", url)
        data = payload.get("data", [])
        comments = [self._parse_comment(item) for item in data if isinstance(item, dict)]

        paging = payload.get("paging", {})
        next_after = None
        if isinstance(paging, dict):
            cursors = paging.get("cursors", {})
            if isinstance(cursors, dict):
                next_after = self._optional_text(cursors.get("after"))

        return ThreadsReplyPage(comments=comments, next_after=next_after)

    def publish_reply(self, reply_to_id: str, text: str) -> str:
        creation = self._create_text_container(text, reply_to_id=reply_to_id)
        creation_id = self._optional_text(creation.get("id"))
        if not creation_id:
            raise ThreadsApiError("Threads reply create response did not include a creation id")

        payload = self._publish_container(creation_id)
        reply_id = self._optional_text(payload.get("id"))
        if reply_id:
            return reply_id

        data = payload.get("data", {})
        if isinstance(data, dict):
            reply_id = self._optional_text(data.get("id"))
            if reply_id:
                return reply_id

        raise ThreadsApiError("Threads reply publish response did not include a reply id")

    def publish_post(self, text: str) -> str:
        creation = self._create_text_container(text)
        creation_id = self._optional_text(creation.get("id"))
        if not creation_id:
            raise ThreadsApiError("Threads create response did not include a creation id")

        self._wait_for_container(creation_id)
        self._log_publish_diagnostic(creation_id)
        payload = self._publish_container(creation_id)
        post_id = self._optional_text(payload.get("id"))
        if post_id:
            return post_id

        data = payload.get("data", {})
        if isinstance(data, dict):
            post_id = self._optional_text(data.get("id"))
            if post_id:
                return post_id

        raise ThreadsApiError("Threads publish response did not include a post id")

    def get_container_status(self, container_id: str) -> dict[str, object]:
        params = {
            "access_token": self.access_token,
            "fields": "id,status,error_message",
        }
        url = f"{self.base_url}/{container_id}?{urlencode(params)}"
        return self._request_json("GET", url)

    def get_publishing_limit(self) -> dict[str, object]:
        """Read Meta's current account publishing quota configuration."""
        params = urlencode({
            "fields": "quota_usage,config,reply_quota_usage,reply_config",
            "access_token": self.access_token,
        })
        url = f"{self.base_url}/{self.user_id}/threads_publishing_limit?{params}"
        return self._request_json("GET", url)

    def _wait_for_container(self, container_id: str) -> None:
        for attempt in range(self.container_poll_attempts):
            payload = self.get_container_status(container_id)
            status = (self._optional_text(payload.get("status")) or "").upper()
            if status == "FINISHED":
                return
            if status in {"ERROR", "EXPIRED", "PUBLISHED"}:
                detail = self._optional_text(payload.get("error_message")) or status
                raise ThreadsApiError(
                    f"Threads container {container_id} is not publishable: {detail}"
                )
            if status not in {"IN_PROGRESS", ""}:
                raise ThreadsApiError(
                    f"Threads container {container_id} returned unexpected status: {status}"
                )
            if attempt < self.container_poll_attempts - 1:
                self.sleep_impl(self.container_poll_seconds)
        raise ThreadsApiError(
            f"Threads container {container_id} did not reach FINISHED status"
        )

    def get_post_permalink(self, post_id: str) -> str | None:
        """Read the permalink after publishing without changing external state."""
        params = urlencode({"fields": "permalink", "access_token": self.access_token})
        url = f"{self.base_url}/{post_id}?{params}"
        payload = self._request_json("GET", url)
        return self._optional_text(payload.get("permalink"))

    def _create_text_container(
        self,
        text: str,
        reply_to_id: str | None = None,
    ) -> dict[str, object]:
        url = f"{self.base_url}/{self.user_id}/threads"
        payload = {
            "access_token": self.access_token,
            "media_type": "TEXT",
            "text": text,
        }
        if reply_to_id is not None:
            payload["reply_to_id"] = reply_to_id
        return self._request_json(
            "POST",
            url,
            data=urlencode(payload).encode("utf-8"),
            content_type="application/x-www-form-urlencoded",
        )

    def _publish_container(self, creation_id: str) -> dict[str, object]:
        url = f"{self.base_url}/{self.user_id}/threads_publish"
        payload = {
            "access_token": self.access_token,
            "creation_id": creation_id,
        }
        return self._request_json(
            "POST",
            url,
            data=urlencode(payload).encode("utf-8"),
            content_type="application/x-www-form-urlencoded",
        )

    def _log_publish_diagnostic(self, creation_id: str) -> None:
        """Expose enough correlation data to debug remote two-step publishing."""
        print(
            "Threads publish diagnostic: "
            f"user_id={self.user_id}; "
            f"create_endpoint={self.base_url}/{self.user_id}/threads; "
            f"publish_endpoint={self.base_url}/{self.user_id}/threads_publish; "
            f"creation_id={self._redact_identifier(creation_id)}"
        )

    @staticmethod
    def _redact_identifier(identifier: str) -> str:
        if len(identifier) <= 8:
            return "<short>"
        return f"{identifier[:4]}...{identifier[-4:]}"

    def _parse_comment(self, item: dict[str, object]) -> ThreadsComment:
        comment_id = self._required_text(item.get("id"), "comment id")
        text = self._optional_text(item.get("text")) or ""
        username = self._optional_text(item.get("username"))
        timestamp = self._optional_text(item.get("timestamp"))
        reply_to_id = self._optional_text(
            item.get("reply_to_id")
            or item.get("replyToId")
            or item.get("parent_id")
            or item.get("parentId")
        )
        return ThreadsComment(
            comment_id=comment_id,
            text=text,
            username=username,
            timestamp=timestamp,
            reply_to_id=reply_to_id,
        )

    def _parse_media_id(self, item: dict[str, object]) -> str:
        return self._required_text(item.get("id"), "media id")

    def _request_json(
        self,
        method: str,
        url: str,
        data: bytes | None = None,
        content_type: str = "application/json",
    ) -> dict[str, object]:
        headers = {
            "Accept": "application/json",
        }
        if content_type:
            headers["Content-Type"] = content_type

        request = Request(url, data=data, headers=headers, method=method)
        try:
            response = self.request_impl(request)
            raw_body = response.read()
            status = getattr(response, "status", 200)
        except HTTPError as exc:
            raw_body = exc.read()
            status = exc.code
        except Exception as exc:  # pragma: no cover - wrapped by caller
            raise ThreadsApiError(f"Threads request failed: {exc}") from exc

        body_text = raw_body.decode("utf-8") if isinstance(raw_body, bytes) else str(raw_body)
        try:
            payload = json.loads(body_text or "{}")
        except json.JSONDecodeError as exc:
            raise ThreadsApiError("Threads response was not valid JSON") from exc

        if status >= 400:
            raise ThreadsApiError(
                f"Threads API returned HTTP {status}: {body_text}".rstrip(),
            )

        if isinstance(payload, dict) and payload.get("error"):
            raise ThreadsApiError(str(payload["error"]))

        if not isinstance(payload, dict):
            raise ThreadsApiError("Threads response payload was not an object")

        return payload

    @staticmethod
    def _required_text(value: object, label: str) -> str:
        text = ThreadsApiClient._optional_text(value)
        if not text:
            raise ThreadsApiError(f"Missing {label}")
        return text

    @staticmethod
    def _optional_text(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
