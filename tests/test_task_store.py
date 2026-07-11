import tempfile
import unittest
from pathlib import Path

from threads_bot_system.reply_action import mark_awaiting_review, mark_drafted
from threads_bot_system.reply_task import new_reply_task
from threads_bot_system.task_store import ReplyTaskStore


class ReplyTaskStoreTests(unittest.TestCase):
    def test_save_and_load_round_trips_reply_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "reply_tasks.json"
            store = ReplyTaskStore.load(path)
            task = mark_awaiting_review(
                mark_drafted(new_reply_task("comment-1"), "draft text"),
                "msg-1",
            )
            store.upsert(task)
            store.save()

            restored = ReplyTaskStore.load(path)
            self.assertEqual(restored.get(task.reply_task_id), task)

    def test_loading_missing_store_returns_empty_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.json"

            store = ReplyTaskStore.load(path)

            self.assertEqual(store.tasks, {})
            self.assertEqual(store.path, path)


if __name__ == "__main__":
    unittest.main()
