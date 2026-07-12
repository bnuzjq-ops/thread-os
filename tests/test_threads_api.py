import json
from urllib.error import HTTPError
import io
import unittest

from threads_bot_system.threads_api import ThreadsApiClient, ThreadsApiError


class DummyResponse:
    def __init__(self, body: str, status: int = 200) -> None:
        self._body = body.encode("utf-8")
        self.status = status

    def read(self) -> bytes:
        return self._body


class ThreadsApiTests(unittest.TestCase):
    def test_http_error_body_is_preserved_in_threads_error(self) -> None:
        def fake_request(request: object) -> DummyResponse:
            raise HTTPError(
                request.full_url,
                400,
                "Bad Request",
                hdrs=None,
                fp=io.BytesIO(b'{"error":"missing permission"}'),
            )

        client = ThreadsApiClient(
            user_id="user-1",
            access_token="token-1",
            request_impl=fake_request,
        )

        with self.assertRaisesRegex(ThreadsApiError, "missing permission"):
            client.fetch_replies("media-1")

    def test_fetch_user_threads_pages_through_results(self) -> None:
        requests: list[object] = []

        def fake_request(request: object) -> DummyResponse:
            requests.append(request)
            if "after=cursor-1" in request.full_url:
                return DummyResponse(json.dumps({"data": [{"id": "media-2"}]}))
            return DummyResponse(
                json.dumps(
                    {
                        "data": [{"id": "media-1"}],
                        "paging": {"cursors": {"after": "cursor-1"}},
                    }
                )
            )

        client = ThreadsApiClient(
            user_id="user-1",
            access_token="token-1",
            request_impl=fake_request,
        )

        media_ids = client.fetch_user_threads(limit=50)

        self.assertEqual(media_ids, ["media-1", "media-2"])
        self.assertEqual(requests[0].get_method(), "GET")
        self.assertIn("/user-1/threads", requests[0].full_url)
        self.assertIn("access_token=token-1", requests[0].full_url)

    def test_fetch_replies_pages_through_results(self) -> None:
        requests: list[object] = []

        def fake_request(request: object) -> DummyResponse:
            requests.append(request)
            if "after=cursor-1" in request.full_url:
                return DummyResponse(
                    json.dumps(
                        {
                            "data": [
                                {
                                    "id": "comment-2",
                                    "text": "第二条评论",
                                    "username": "user-2",
                                    "timestamp": "2026-07-10T10:01:00Z",
                                }
                            ]
                        }
                    )
                )
            return DummyResponse(
                json.dumps(
                    {
                        "data": [
                            {
                                "id": "comment-1",
                                "text": "第一条评论",
                                "username": "user-1",
                                "timestamp": "2026-07-10T10:00:00Z",
                            }
                        ],
                        "paging": {"cursors": {"after": "cursor-1"}},
                    }
                )
            )

        client = ThreadsApiClient(
            user_id="user-1",
            access_token="token-1",
            request_impl=fake_request,
        )

        comments = client.fetch_replies("media-1", limit=50)

        self.assertEqual([comment.comment_id for comment in comments], ["comment-1", "comment-2"])
        self.assertEqual(requests[0].get_method(), "GET")
        self.assertIn("/media-1/replies", requests[0].full_url)
        self.assertIn("access_token=token-1", requests[0].full_url)

    def test_publish_reply_returns_response_id(self) -> None:
        requests: list[object] = []

        def fake_request(request: object) -> DummyResponse:
            requests.append(request)
            return DummyResponse(json.dumps({"id": "reply-1"}))

        client = ThreadsApiClient(
            user_id="user-1",
            access_token="token-1",
            request_impl=fake_request,
        )

        reply_id = client.publish_reply(reply_to_id="comment-1", text="谢谢你的提问")

        self.assertEqual(reply_id, "reply-1")
        self.assertEqual(requests[0].get_method(), "POST")
        body = requests[0].data.decode("utf-8")
        self.assertIn("reply_to_id=comment-1", body)
        self.assertIn("text=%E8%B0%A2%E8%B0%A2%E4%BD%A0%E7%9A%84%E6%8F%90%E9%97%AE", body)

    def test_publish_post_returns_response_id(self) -> None:
        requests: list[object] = []

        def fake_request(request: object) -> DummyResponse:
            requests.append(request)
            if request.full_url.endswith("/threads"):
                return DummyResponse(json.dumps({"id": "creation-1"}))
            return DummyResponse(json.dumps({"id": "post-1"}))

        client = ThreadsApiClient(
            user_id="user-1",
            access_token="token-1",
            request_impl=fake_request,
        )

        post_id = client.publish_post(text="Hello Threads")

        self.assertEqual(post_id, "post-1")
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0].get_method(), "POST")
        create_body = requests[0].data.decode("utf-8")
        self.assertIn("media_type=TEXT", create_body)
        self.assertIn("text=Hello+Threads", create_body)
        publish_body = requests[1].data.decode("utf-8")
        self.assertIn("creation_id=creation-1", publish_body)


if __name__ == "__main__":
    unittest.main()
