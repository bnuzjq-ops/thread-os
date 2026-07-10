import unittest

from threads_bot_system.reply_policy import ReplyRoute, build_reply_plan


class ReplyPlanTests(unittest.TestCase):
    def test_low_signal_comment_builds_like_only_plan(self) -> None:
        plan = build_reply_plan("666")

        self.assertEqual(plan.decision.route, ReplyRoute.LIKE_ONLY)
        self.assertTrue(plan.should_like)
        self.assertFalse(plan.needs_review)

    def test_meaningful_question_builds_review_plan(self) -> None:
        plan = build_reply_plan("这篇文章为什么这样设计？")

        self.assertEqual(plan.decision.route, ReplyRoute.REVIEW)
        self.assertFalse(plan.should_like)
        self.assertTrue(plan.needs_review)


if __name__ == "__main__":
    unittest.main()
