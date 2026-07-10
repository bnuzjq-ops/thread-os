import unittest

from threads_bot_system.reply_task import ReplyTaskStatus, new_reply_task


class ReplyTaskTests(unittest.TestCase):
    def test_new_reply_task_uses_comment_id_based_identifier(self) -> None:
        task = new_reply_task("comment-1")

        self.assertEqual(task.reply_task_id, "reply:comment-1")
        self.assertEqual(task.comment_id, "comment-1")
        self.assertEqual(task.status, ReplyTaskStatus.DETECTED)

    def test_new_reply_task_has_empty_optional_fields(self) -> None:
        task = new_reply_task("comment-1")

        self.assertEqual(task.draft, "")
        self.assertEqual(task.draft_version, 0)
        self.assertIsNone(task.feishu_message_id)
        self.assertIsNone(task.reply_id)
        self.assertIsNone(task.last_error)


if __name__ == "__main__":
    unittest.main()
