import json
import unittest

from threads_bot_system.deepseek_api import DeepSeekApiError, DeepSeekClient
from threads_bot_system.reply_flow import prepare_reply_intake


class DummyResponse:
    def __init__(self, body: str, status: int = 200) -> None:
        self._body = body.encode("utf-8")
        self.status = status

    def read(self) -> bytes:
        return self._body


class DeepSeekApiTests(unittest.TestCase):
    def test_generate_reply_draft_uses_chat_completions_response(self) -> None:
        requests: list[object] = []

        def fake_request(request: object) -> DummyResponse:
            requests.append(request)
            return DummyResponse(
                json.dumps(
                    {
                        "choices": [
                            {
                                "message": {
                                    "content": "当然可以，我来补充一下这个点。"
                                }
                            }
                        ]
                    }
                )
            )

        client = DeepSeekClient(
            api_key="deepseek-key",
            request_impl=fake_request,
        )
        intake = prepare_reply_intake("comment-1", "这篇文章为什么这样设计？")

        draft = client.generate_reply_draft(intake)

        self.assertEqual(draft.comment_id, "comment-1")
        self.assertEqual(draft.text, "当然可以，我来补充一下这个点。")
        self.assertEqual(len(requests), 1)
        request = requests[0]
        self.assertIn("chat/completions", request.full_url)
        self.assertEqual(request.get_header("Authorization"), "Bearer deepseek-key")
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["model"], "deepseek-v4-flash")
        self.assertIn("untrusted data", body["messages"][0]["content"])
        self.assertEqual(body["messages"][1]["content"].splitlines()[-1], "这篇文章为什么这样设计？")


if __name__ == "__main__":
    unittest.main()


class DeepSeekErrorPathTests(unittest.TestCase):
    def test_http_error_is_classified_with_status_and_body(self) -> None:
        client = DeepSeekClient(
            api_key="deepseek-key",
            request_impl=lambda request: DummyResponse('{"error":"invalid api key"}', status=401),
        )
        intake = prepare_reply_intake("comment-1", "test")
        with self.assertRaisesRegex(DeepSeekApiError, "HTTP 401.*invalid api key"):
            client.generate_reply_draft(intake)

    def test_invalid_json_is_rejected(self) -> None:
        client = DeepSeekClient(
            api_key="deepseek-key",
            request_impl=lambda request: DummyResponse("not-json"),
        )
        intake = prepare_reply_intake("comment-1", "test")
        with self.assertRaisesRegex(DeepSeekApiError, "not valid JSON"):
            client.generate_reply_draft(intake)

    def test_empty_message_content_is_rejected(self) -> None:
        client = DeepSeekClient(
            api_key="deepseek-key",
            request_impl=lambda request: DummyResponse(
                json.dumps({"choices": [{"message": {"content": "   "}}]})
            ),
        )
        intake = prepare_reply_intake("comment-1", "test")
        with self.assertRaisesRegex(DeepSeekApiError, "did not include message content"):
            client.generate_reply_draft(intake)
