import json
import tempfile
import unittest
from pathlib import Path

from threads_bot_system.reply_action import mark_awaiting_review, mark_drafted, mark_failed
from threads_bot_system.reply_draft import ReplyDraft
from threads_bot_system.reply_runtime import execute_reply_dispatch, run_reply_monitor
from threads_bot_system.reply_state import task_to_record
from threads_bot_system.reply_task import ReplyTaskStatus, new_reply_task
from threads_bot_system.state_api_task_store import StateApiTaskStore, StateApiTaskStoreError
from threads_bot_system.task_store import JsonTaskStore
from threads_bot_system.threads_api import ThreadsComment


class DummyResponse:
    def __init__(self, body: str, status: int = 200) -> None:
        self._body = body.encode("utf-8")
        self.status = status

    def read(self) -> bytes:
        return self._body


class FakeThreadsClient:
    def __init__(self, comments: list[ThreadsComment], *, timeout: bool = False) -> None:
        self.comments = comments
        self.timeout = timeout
        self.published: list[tuple[str, str]] = []
        self.user_replies: list[ThreadsComment] = []

    def fetch_replies(self, media_id: str, limit: int = 100) -> list[ThreadsComment]:
        return self.comments

    def fetch_user_replies(self, limit: int = 100) -> list[ThreadsComment]:
        return self.user_replies

    def publish_reply(self, reply_to_id: str, text: str) -> str:
        if self.timeout:
            raise TimeoutError("reply timed out")
        self.published.append((reply_to_id, text))
        return "reply-1"


class FakeFeishuClient:
    def __init__(self) -> None:
        self.cards: list[object] = []

    def send_review_card(self, payload: object) -> str:
        self.cards.append(payload)
        return "msg-1"

    def send_text_message(self, text: str) -> str:
        self.cards.append(text)
        return "msg-result"


class FakeDeepSeekClient:
    def __init__(self) -> None:
        self.inputs: list[str] = []

    def generate_reply_draft(self, intake) -> ReplyDraft:
        self.inputs.append(intake.text)
        return ReplyDraft(
            comment_id=intake.comment_id,
            text="Generated draft text",
            version=1,
        )


class FailingDeepSeekClient:
    def generate_reply_draft(self, intake) -> ReplyDraft:
        raise RuntimeError("deepseek unavailable")


class ReplyRuntimeTests(unittest.TestCase):
    def test_run_reply_monitor_builds_cards_and_persists_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "reply_tasks.json"
            store = JsonTaskStore.load(store_path)
            store.upsert(new_reply_task("seed-comment"))
            store.save()
            threads_client = FakeThreadsClient(
                [
                    ThreadsComment(comment_id="comment-1", text="666"),
                    ThreadsComment(comment_id="comment-2", text="How should we reply to this?"),
                ]
            )
            feishu_client = FakeFeishuClient()
            deepseek_client = FakeDeepSeekClient()

            report = run_reply_monitor(
                ["media-1"],
                threads_client,
                feishu_client,
                store_path,
                deepseek_client=deepseek_client,
            )

            self.assertEqual(report.like_only_count, 1)
            self.assertEqual(report.review_count, 1)
            self.assertEqual(len(feishu_client.cards), 1)
            self.assertIn("Generated draft text", feishu_client.cards[0].body)

            restored = JsonTaskStore.load(store_path)
            task = restored.get("reply:comment-2")
            self.assertIsNotNone(task)
            self.assertEqual(task.status, ReplyTaskStatus.AWAITING_REVIEW)
            self.assertEqual(task.feishu_message_id, "msg-1")
            self.assertEqual(task.draft, "Generated draft text")

    def test_run_reply_monitor_backfills_when_store_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "reply_tasks.json"
            threads_client = FakeThreadsClient(
                [ThreadsComment(comment_id="comment-2", text="How should we reply to this?")]
            )
            feishu_client = FakeFeishuClient()
            deepseek_client = FakeDeepSeekClient()

            report = run_reply_monitor(
                ["media-1"],
                threads_client,
                feishu_client,
                store_path,
                deepseek_client=deepseek_client,
            )

            self.assertEqual(report.review_count, 1)
            self.assertEqual(len(feishu_client.cards), 1)
            self.assertTrue(store_path.exists())

            restored = JsonTaskStore.load(store_path)
            task = restored.get("reply:comment-2")
            self.assertIsNotNone(task)
            self.assertEqual(task.status, ReplyTaskStatus.AWAITING_REVIEW)
            self.assertEqual(task.feishu_message_id, "msg-1")

    def test_run_reply_monitor_skips_comments_already_replied_by_user(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "reply_tasks.json"
            threads_client = FakeThreadsClient(
                [ThreadsComment(comment_id="comment-2", text="How should we reply to this?")]
            )
            threads_client.user_replies = [
                ThreadsComment(comment_id="reply-1", text="I already answered", reply_to_id="comment-2")
            ]
            feishu_client = FakeFeishuClient()
            deepseek_client = FakeDeepSeekClient()

            report = run_reply_monitor(
                ["media-1"],
                threads_client,
                feishu_client,
                store_path,
                deepseek_client=deepseek_client,
            )

            self.assertEqual(report.review_count, 0)
            self.assertEqual(feishu_client.cards, [])
            self.assertFalse(store_path.exists())

    def test_run_reply_monitor_does_not_retry_failed_tasks_automatically(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "reply_tasks.json"
            store = JsonTaskStore.load(store_path)
            store.upsert(mark_failed(new_reply_task("comment-fail"), "feishu card rejected"))
            store.save()
            threads_client = FakeThreadsClient(
                [ThreadsComment(comment_id="comment-fail", text="How should we reply to this?")]
            )
            feishu_client = FakeFeishuClient()
            deepseek_client = FakeDeepSeekClient()

            report = run_reply_monitor(
                ["media-1"],
                threads_client,
                feishu_client,
                store_path,
                deepseek_client=deepseek_client,
            )

            self.assertEqual(report.review_count, 1)
            self.assertEqual(deepseek_client.inputs, [])
            self.assertEqual(feishu_client.cards, [])
            restored = JsonTaskStore.load(store_path)
            task = restored.get("reply:comment-fail")
            self.assertIsNotNone(task)
            self.assertEqual(task.status, ReplyTaskStatus.FAILED)
            self.assertEqual(task.last_error, "feishu card rejected")

    def test_execute_reply_dispatch_sends_reply_and_updates_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "reply_tasks.json"
            store = JsonTaskStore.load(store_path)
            task = mark_awaiting_review(mark_drafted(new_reply_task("comment-2"), "Generated draft text"), "msg-1")
            store.upsert(task)
            store.save()

            threads_client = FakeThreadsClient([])
            updated = execute_reply_dispatch(
                {
                    "action": "send",
                    "reply_task_id": "reply:comment-2",
                },
                threads_client,
                store_path,
            )

            self.assertEqual(updated.status, ReplyTaskStatus.SENT)
            self.assertEqual(updated.reply_id, "reply-1")
            self.assertEqual(threads_client.published, [("comment-2", "Generated draft text")])

            restored = JsonTaskStore.load(store_path)
            self.assertEqual(restored.get("reply:comment-2").status, ReplyTaskStatus.SENT)

    def test_execute_reply_dispatch_notifies_feishu_after_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "reply_tasks.json"
            store = JsonTaskStore.load(store_path)
            task = mark_awaiting_review(mark_drafted(new_reply_task("comment-result"), "draft"), "msg-1")
            store.upsert(task)
            store.save()
            feishu_client = FakeFeishuClient()

            execute_reply_dispatch(
                {"action": "send", "reply_task_id": task.reply_task_id},
                FakeThreadsClient([]),
                store_path,
                feishu_client=feishu_client,
            )

            self.assertEqual(feishu_client.cards, ["Threads 回复已发送：reply-1"])

    def test_execute_reply_dispatch_stops_when_state_api_unavailable(self) -> None:
        task = mark_drafted(new_reply_task("comment-3"), "Generated draft text")

        def fake_request(request: object) -> DummyResponse:
            if request.get_method() == "GET":
                return DummyResponse(json.dumps({"ok": True, "task": task_to_record(task)}))
            raise OSError("state api unavailable")

        store = StateApiTaskStore(
            base_url="https://state.example",
            api_token="state-token",
            request_impl=fake_request,
        )
        threads_client = FakeThreadsClient([])

        with self.assertRaises(StateApiTaskStoreError):
            execute_reply_dispatch(
                {
                    "action": "send",
                    "reply_task_id": "reply:comment-3",
                },
                threads_client,
                store,
            )

        self.assertEqual(threads_client.published, [])

    def test_run_reply_monitor_records_deepseek_failure_without_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "reply_tasks.json"
            store = JsonTaskStore.load(store_path)
            store.upsert(new_reply_task("seed-comment"))
            store.save()
            threads_client = FakeThreadsClient(
                [ThreadsComment(comment_id="comment-fail", text="Why this design?")]
            )
            feishu_client = FakeFeishuClient()

            run_reply_monitor(
                ["media-1"],
                threads_client,
                feishu_client,
                store_path,
                deepseek_client=FailingDeepSeekClient(),
            )

            task = JsonTaskStore.load(store_path).get("reply:comment-fail")
            self.assertEqual(task.status, ReplyTaskStatus.FAILED)
            self.assertIn("deepseek unavailable", task.last_error)
            self.assertEqual(feishu_client.cards, [])

    def test_execute_reply_dispatch_skips_missing_task_without_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "reply_tasks.json"
            threads_client = FakeThreadsClient([])

            updated = execute_reply_dispatch(
                {
                    "action": "skip",
                    "reply_task_id": "reply:old-comment",
                },
                threads_client,
                store_path,
            )

            self.assertEqual(updated.status, ReplyTaskStatus.SKIPPED)
            self.assertEqual(updated.reply_id, None)
            self.assertEqual(updated.last_error, "Reply task not found for action: skip")
            self.assertEqual(threads_client.published, [])
            self.assertFalse(store_path.exists())

    def test_execute_reply_dispatch_marks_timeout_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "reply_tasks.json"
            store = JsonTaskStore.load(store_path)
            task = mark_awaiting_review(mark_drafted(new_reply_task("comment-timeout"), "draft"), "msg-1")
            store.upsert(task)
            store.save()

            with self.assertRaises(TimeoutError):
                execute_reply_dispatch(
                    {"action": "send", "reply_task_id": "reply:comment-timeout"},
                    FakeThreadsClient([], timeout=True),
                    store_path,
                )

            updated = JsonTaskStore.load(store_path).get(task.reply_task_id)
            self.assertEqual(updated.status, ReplyTaskStatus.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
