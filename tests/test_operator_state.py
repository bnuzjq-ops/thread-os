import tempfile
import unittest
from pathlib import Path

from threads_bot_system.operator_state import (
    OperatorStateStore,
    active_task_for,
    select_next_review_task,
)
from threads_bot_system.reply_action import mark_awaiting_review, mark_drafted
from threads_bot_system.reply_task import ReplyTaskStatus, new_reply_task


class OperatorStateTests(unittest.TestCase):
    def _task(self, comment_id: str, created_at: str):
        task = mark_awaiting_review(mark_drafted(new_reply_task(comment_id), "draft"), "msg")
        task.created_at = created_at
        return task

    def test_next_review_persists_deterministic_active_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = OperatorStateStore.load(Path(tmpdir) / "operator.json")
            tasks = [self._task("later", "2026-07-13T02:00:00Z"), self._task("first", "2026-07-13T01:00:00Z")]

            selected = select_next_review_task(tasks, "ou_user", state)

            self.assertEqual(selected.reply_task_id, "reply:first")
            restored = OperatorStateStore.load(state.path)
            self.assertEqual(restored.get("ou_user").active_task_id, "reply:first")

    def test_terminal_active_task_is_not_actionable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = OperatorStateStore.load(Path(tmpdir) / "operator.json")
            task = self._task("done", "2026-07-13T01:00:00Z")
            state.set_active("ou_user", task.reply_task_id)
            task.status = ReplyTaskStatus.SKIPPED

            self.assertIsNone(active_task_for([task], "ou_user", state))

    def test_no_review_task_clears_previous_selection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = OperatorStateStore.load(Path(tmpdir) / "operator.json")
            state.set_active("ou_user", "reply:old")

            self.assertIsNone(select_next_review_task([], "ou_user", state))
            self.assertIsNone(state.get("ou_user").active_task_id)


if __name__ == "__main__":
    unittest.main()
