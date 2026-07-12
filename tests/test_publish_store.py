import tempfile
import unittest
from pathlib import Path

from threads_bot_system.publish_store import JsonPublishStore
from threads_bot_system.publish_task import PublishTaskStatus


class PublishStoreTests(unittest.TestCase):
    def test_save_and_load_round_trip_publish_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "publish_tasks.json"
            store = JsonPublishStore.load(path)

            created = store.create_task("draft-1", "First post")
            store.save()

            restored = JsonPublishStore.load(path)

            self.assertTrue(created.ok)
            self.assertTrue(created.created)
            self.assertEqual(restored.get_task(created.task.publish_task_id), created.task)

    def test_create_task_is_idempotent_for_the_same_source_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "publish_tasks.json"
            store = JsonPublishStore.load(path)

            first = store.create_task("draft-1", "First post")
            second = store.create_task("draft-1", "First post")

            self.assertTrue(first.ok)
            self.assertTrue(first.created)
            self.assertFalse(second.created)
            self.assertTrue(second.already_exists)
            self.assertEqual(first.task.publish_task_id, second.task.publish_task_id)
            self.assertIsNotNone(first.task.created_at)
            self.assertIsNotNone(first.task.updated_at)
            self.assertEqual(first.task.status, PublishTaskStatus.READY)

    def test_legacy_pending_state_loads_as_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "publish_tasks.json"
            path.write_text(
                '{"tasks": {"publish:draft-1": {'
                '"publish_task_id": "publish:draft-1", "source_key": "draft-1", '
                '"text": "First post", "status": "pending"}}}',
                encoding="utf-8",
            )

            restored = JsonPublishStore.load(path)

            self.assertEqual(
                restored.get_task("publish:draft-1").status,
                PublishTaskStatus.READY,
            )


if __name__ == "__main__":
    unittest.main()
