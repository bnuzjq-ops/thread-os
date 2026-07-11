import tempfile
import unittest
from pathlib import Path

from threads_bot_system.publish_runtime import PublishRunError, run_publish
from threads_bot_system.publish_store import JsonPublishStore
from threads_bot_system.publish_task import PublishTaskStatus


class FakeThreadsClient:
    def __init__(self, *, fail: bool = False, timeout: bool = False) -> None:
        self.fail = fail
        self.timeout = timeout
        self.published_texts: list[str] = []

    def publish_post(self, text: str) -> str:
        if self.timeout:
            raise TimeoutError("publish timed out")
        if self.fail:
            raise RuntimeError("publish failed")
        self.published_texts.append(text)
        return f"post-{len(self.published_texts)}"


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

    def test_run_publish_marks_timeout_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "publish_tasks.json"
            store = JsonPublishStore.load(path)
            task = store.create_task("draft-timeout", "Hello Threads").task

            with self.assertRaises(PublishRunError):
                run_publish(store, FakeThreadsClient(timeout=True))

            updated = JsonPublishStore.load(path).get_task(task.publish_task_id)
            self.assertEqual(updated.status, PublishTaskStatus.UNKNOWN)

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


if __name__ == "__main__":
    unittest.main()
