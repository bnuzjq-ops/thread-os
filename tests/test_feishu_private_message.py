import json
import unittest
from urllib.request import Request

from threads_bot_system.feishu_api import FeishuClient


class _Response:
    status = 200

    def read(self):
        return json.dumps({"code": 0, "data": {"message_id": "om_private"}}).encode()


class FeishuPrivateMessageTests(unittest.TestCase):
    def test_private_text_uses_open_id_recipient_type(self):
        requests = []

        def request_impl(request: Request):
            requests.append(request)
            if request.full_url.endswith("/auth/v3/tenant_access_token/internal/"):
                return type("TokenResponse", (), {"status": 200, "read": lambda self: b'{"code":0,"tenant_access_token":"token"}'})()
            return _Response()

        client = FeishuClient("app", "secret", "chat", request_impl=request_impl)
        self.assertEqual(client.send_text_message_to_open_id("ou_user", "hello"), "om_private")
        message_request = requests[-1]
        self.assertIn("receive_id_type=open_id", message_request.full_url)
        body = json.loads(message_request.data.decode())
        self.assertEqual(body["receive_id"], "ou_user")
        self.assertEqual(json.loads(body["content"])["text"], "hello")


if __name__ == "__main__":
    unittest.main()
