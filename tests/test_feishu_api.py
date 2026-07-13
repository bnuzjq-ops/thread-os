import json
import io
import unittest
from urllib.error import HTTPError

from threads_bot_system.feishu_api import FeishuApiError, FeishuClient
from threads_bot_system.reply_card import ReplyCardAction, ReplyCardPayload


class DummyResponse:
    def __init__(self, body: str, status: int = 200) -> None:
        self._body = body.encode("utf-8")
        self.status = status

    def read(self) -> bytes:
        return self._body


class FeishuApiTests(unittest.TestCase):
    def test_http_error_preserves_feishu_response_body(self) -> None:
        def fake_request(request: object) -> DummyResponse:
            raise HTTPError(
                request.full_url,
                400,
                "Bad Request",
                hdrs=None,
                fp=io.BytesIO(b'{"code":99991663,"msg":"invalid receive_id"}'),
            )

        client = FeishuClient(
            app_id="app-id",
            app_secret="app-secret",
            chat_id="chat-id",
            request_impl=fake_request,
        )

        with self.assertRaisesRegex(FeishuApiError, "invalid receive_id"):
            client.send_text_message("test")
    def test_send_review_card_uses_tenant_token_and_interactive_payload(self) -> None:
        requests: list[object] = []

        def fake_request(request: object) -> DummyResponse:
            requests.append(request)
            if "tenant_access_token" in request.full_url:
                return DummyResponse(json.dumps({"tenant_access_token": "tenant-token"}))
            return DummyResponse(json.dumps({"data": {"message_id": "om_1"}}))

        client = FeishuClient(
            app_id="app-id",
            app_secret="app-secret",
            chat_id="chat-id",
            request_impl=fake_request,
        )
        payload = ReplyCardPayload(
            title="回复审核 · comment-1",
            body="评论内容：你好",
            actions=[ReplyCardAction(label="发送", value="send:reply:comment-1")],
        )

        message_id = client.send_review_card(payload)

        self.assertEqual(message_id, "om_1")
        self.assertEqual(len(requests), 2)
        self.assertIn("tenant_access_token/internal", requests[0].full_url)
        self.assertIn("/im/v1/messages", requests[1].full_url)
        body = json.loads(requests[1].data.decode("utf-8"))
        self.assertEqual(body["receive_id"], "chat-id")
        self.assertEqual(body["msg_type"], "interactive")
        content = json.loads(body["content"])
        self.assertEqual(content["schema"], "2.0")
        self.assertEqual(content["header"]["title"]["content"], "回复审核 · comment-1")
        self.assertEqual(
            content["body"]["elements"][1]["behaviors"][0]["value"],
            {"action": "send", "reply_task_id": "reply:comment-1"},
        )

    def test_send_text_message_uses_text_payload(self) -> None:
        requests: list[object] = []

        def fake_request(request: object) -> DummyResponse:
            requests.append(request)
            if "tenant_access_token" in request.full_url:
                return DummyResponse(json.dumps({"tenant_access_token": "tenant-token"}))
            return DummyResponse(json.dumps({"data": {"message_id": "om_result"}}))

        client = FeishuClient(
            app_id="app-id",
            app_secret="app-secret",
            chat_id="chat-id",
            request_impl=fake_request,
        )

        message_id = client.send_text_message("已发送 reply-1")

        self.assertEqual(message_id, "om_result")
        body = json.loads(requests[1].data.decode("utf-8"))
        self.assertEqual(body["msg_type"], "text")
        self.assertEqual(json.loads(body["content"])["text"], "已发送 reply-1")


    def test_update_review_card_reuses_message_id(self) -> None:
        requests: list[object] = []

        def fake_request(request: object) -> DummyResponse:
            requests.append(request)
            if "tenant_access_token" in request.full_url:
                return DummyResponse(json.dumps({"tenant_access_token": "tenant-token"}))
            return DummyResponse('{"code":0}')

        client = FeishuClient(
            app_id="app-id",
            app_secret="app-secret",
            chat_id="chat-id",
            request_impl=fake_request,
        )
        client.update_review_card("om_1", "sending", "processing")

        self.assertEqual(requests[1].get_method(), "PUT")
        self.assertIn("/im/v1/messages/om_1", requests[1].full_url)


if __name__ == "__main__":
    unittest.main()
