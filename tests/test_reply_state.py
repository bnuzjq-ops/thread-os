import unittest

from threads_bot_system.reply_state import task_from_record, task_to_record
from threads_bot_system.reply_action import mark_awaiting_review
from threads_bot_system.reply_task import ReplyTaskStatus, new_reply_task


class ReplyStateTests(unittest.TestCase):
    def test_task_round_trips_through_record(self) -> None:
        task = new_reply_task("comment-1")

        record = task_to_record(task)
        restored = task_from_record(record)

        self.assertEqual(restored, task)

    def test_partial_record_fills_default_optional_fields(self) -> None:
        task = task_from_record(
            {
                "reply_task_id": "reply:comment-1",
                "comment_id": "comment-1",
                "status": "detected",
            }
        )

        self.assertEqual(task.reply_task_id, "reply:comment-1")
        self.assertEqual(task.comment_id, "comment-1")
        self.assertEqual(task.status, ReplyTaskStatus.DETECTED)
        self.assertEqual(task.draft, "")
        self.assertEqual(task.draft_version, 0)
        self.assertIsNone(task.feishu_message_id)
        self.assertIsNone(task.reply_id)
        self.assertIsNone(task.last_error)

    def test_task_record_exposes_card_message_id_alias(self) -> None:
        task = mark_awaiting_review(new_reply_task("comment-card"), "msg-card")
        record = task_to_record(task)
        self.assertEqual(record["card_message_id"], "msg-card")
        restored = task_from_record(
            {
                "reply_task_id": "reply:legacy",
                "comment_id": "legacy",
                "status": "awaiting_review",
                "card_message_id": "msg-legacy",
            }
        )
        self.assertEqual(restored.feishu_message_id, "msg-legacy")


if __name__ == "__main__":
    unittest.main()
