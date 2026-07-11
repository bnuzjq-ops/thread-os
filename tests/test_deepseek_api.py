import json
import unittest

from threads_bot_system.deepseek_api import DeepSeekClient
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
        self.assertEqual(body["messages"][1]["content"].splitlines()[-1], "这篇文章为什么这样设计？")


if __name__ == "__main__":
    unittest.main()
