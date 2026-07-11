"""Small Threads API client for reply monitoring and sending."""

from __future__ import annotations

import json
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
        payload = self._publish_text(text=text, reply_to_id=reply_to_id)
        reply_id = self._optional_text(payload.get("id"))
        if reply_id:
            return reply_id

        data = payload.get("data", {})
        if isinstance(data, dict):
            reply_id = self._optional_text(data.get("id"))
            if reply_id:
                return reply_id

        raise ThreadsApiError("Threads publish response did not include a reply id")

    def publish_post(self, text: str) -> str:
        payload = self._publish_text(text=text)
        post_id = self._optional_text(payload.get("id"))
        if post_id:
            return post_id

        data = payload.get("data", {})
        if isinstance(data, dict):
            post_id = self._optional_text(data.get("id"))
            if post_id:
                return post_id

        raise ThreadsApiError("Threads publish response did not include a post id")

    def _publish_text(self, text: str, reply_to_id: str | None = None) -> dict[str, object]:
        url = f"{self.base_url}/{self.user_id}/threads_publish"
        payload: dict[str, str] = {
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
