import unittest

from threads_bot_system.reply_policy import ReplyRoute, classify_comment


class ReplyPolicyTests(unittest.TestCase):
    def test_blank_comment_goes_like_only(self) -> None:
        decision = classify_comment("   ")

        self.assertEqual(decision.route, ReplyRoute.LIKE_ONLY)
        self.assertEqual(decision.reason, "empty_comment")

    def test_low_signal_comment_goes_like_only(self) -> None:
        decision = classify_comment("666")

        self.assertEqual(decision.route, ReplyRoute.LIKE_ONLY)
        self.assertEqual(decision.reason, "low_signal_comment")

    def test_meaningful_question_goes_review(self) -> None:
        decision = classify_comment("这篇文章为什么这样设计？")

        self.assertEqual(decision.route, ReplyRoute.REVIEW)
        self.assertEqual(decision.reason, "needs_review")


if __name__ == "__main__":
    unittest.main()
