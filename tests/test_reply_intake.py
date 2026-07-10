import unittest

from threads_bot_system.reply_flow import prepare_reply_intake
from threads_bot_system.reply_policy import ReplyRoute
from threads_bot_system.reply_task import ReplyTaskStatus


class ReplyIntakeTests(unittest.TestCase):
    def test_low_signal_comment_has_no_task(self) -> None:
        intake = prepare_reply_intake("comment-1", "666")

        self.assertEqual(intake.decision.route, ReplyRoute.LIKE_ONLY)
        self.assertTrue(intake.plan.should_like)
        self.assertIsNone(intake.task)

    def test_meaningful_comment_creates_reply_task(self) -> None:
        intake = prepare_reply_intake("comment-1", "这篇文章为什么这样设计？")

        self.assertEqual(intake.decision.route, ReplyRoute.REVIEW)
        self.assertTrue(intake.plan.needs_review)
        self.assertIsNotNone(intake.task)
        self.assertEqual(intake.task.reply_task_id, "reply:comment-1")
        self.assertEqual(intake.task.status, ReplyTaskStatus.DETECTED)


if __name__ == "__main__":
    unittest.main()
