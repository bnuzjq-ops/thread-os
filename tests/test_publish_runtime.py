import tempfile
import unittest
from tempfile import TemporaryDirectory
from datetime import datetime, timedelta, timezone
from pathlib import Path

from threads_bot_system.publish_runtime import PublishRunError, run_publish
from threads_bot_system.publish_store import JsonPublishStore
from threads_bot_system.publish_task import PublishTaskStatus


class FakeThreadsClient:
    def __init__(self, *, fail: bool = False, timeout: bool = False, permalink_fail: bool = False) -> None:
        self.fail = fail
        self.timeout = timeout
        self.permalink_fail = permalink_fail
        self.published_texts: list[str] = []

    def publish_post(self, text: str) -> str:
        if self.timeout:
            raise TimeoutError("publish timed out")
        if self.fail:
            raise RuntimeError("publish failed")
        self.published_texts.append(text)
        return f"post-{len(self.published_texts)}"

    def get_post_permalink(self, post_id: str) -> str:
        if self.permalink_fail:
            raise RuntimeError("permalink unavailable")
        return f"https://www.threads.com/post/{post_id}"


class PublishRuntimeTests(unittest.TestCase):
    def test_run_publish_posts_pending_tasks_and_updates_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "publish_tasks.json"
            store = JsonPublishStore.load(path)
            task = store.create_task("draft-1", "Hello Threads").task
            store.save()

            client = FakeThreadsClient()
            report = run_publish(store, client)

            updated = JsonPublishStore.load(path).get_task(task.publish_task_id)

            self.assertEqual(report.attempted, 1)
            self.assertEqual(report.posted, 1)
            self.assertEqual(client.published_texts, ["Hello Threads"])
            self.assertIsNotNone(updated)
            self.assertEqual(updated.status, PublishTaskStatus.PUBLISHED)
            self.assertEqual(updated.post_id, "post-1")
            self.assertEqual(updated.permalink, "https://www.threads.com/post/post-1")
            self.assertIsNotNone(updated.claimed_at)
            self.assertIsNotNone(updated.updated_at)

    def test_run_publish_skips_future_scheduled_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "publish_tasks.json"
            store = JsonPublishStore.load(path)
            future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            task = store.create_task("future", "Not yet", future).task

            report = run_publish(store, FakeThreadsClient())
            self.assertEqual(report.posted, 0)
            self.assertEqual(JsonPublishStore.load(path).get_task(task.publish_task_id).status, PublishTaskStatus.READY)

        self.assertEqual(report.attempted, 0)

    def test_run_publish_can_target_one_task(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = JsonPublishStore.load(Path(tmpdir) / "state.json")
            first = store.create_task("first", "First").task
            second = store.create_task("second", "Second").task
            report = run_publish(store, FakeThreadsClient(), task_ids=[first.publish_task_id])
            self.assertEqual(report.attempted, 1)
            self.assertEqual(report.posted, 1)
            self.assertEqual(store.get(second.publish_task_id).status, PublishTaskStatus.READY)

    def test_permalink_failure_keeps_published_state_without_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "publish_tasks.json"
            store = JsonPublishStore.load(path)
            task = store.create_task("permalink-failure", "Hello Threads").task

            report = run_publish(store, FakeThreadsClient(permalink_fail=True))
            updated = JsonPublishStore.load(path).get_task(task.publish_task_id)

            self.assertEqual(report.posted, 1)
            self.assertEqual(updated.status, PublishTaskStatus.PUBLISHED)
            self.assertEqual(updated.post_id, "post-1")
            self.assertIn("permalink lookup failed", updated.last_error)

    def test_run_publish_marks_timeout_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "publish_tasks.json"
            store = JsonPublishStore.load(path)
            task = store.create_task("draft-timeout", "Hello Threads").task

            with self.assertRaises(PublishRunError):
                run_publish(store, FakeThreadsClient(timeout=True))

            updated = JsonPublishStore.load(path).get_task(task.publish_task_id)
            self.assertEqual(updated.status, PublishTaskStatus.UNKNOWN)
            self.assertEqual(updated.error_type, "unknown_result")
            self.assertEqual(updated.error_phase, "threads_publish")
            self.assertTrue(updated.external_action)
            self.assertFalse(updated.retry_allowed)

    def test_run_publish_raises_when_every_attempt_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "publish_tasks.json"
            store = JsonPublishStore.load(path)
            task = store.create_task("draft-1", "Hello Threads").task
            store.save()

            client = FakeThreadsClient(fail=True)

            with self.assertRaises(PublishRunError):
                run_publish(store, client)

            updated = JsonPublishStore.load(path).get_task(task.publish_task_id)
            self.assertIsNotNone(updated)
            self.assertEqual(updated.status, PublishTaskStatus.FAILED)
            self.assertEqual(updated.error_phase, "threads_publish")
            self.assertFalse(updated.external_action)
            self.assertFalse(updated.retry_allowed)


if __name__ == "__main__":
    unittest.main()
