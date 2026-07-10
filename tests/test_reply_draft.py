import unittest

from threads_bot_system.reply_draft import ReplyDraft, build_reply_draft
from threads_bot_system.reply_flow import prepare_reply_intake


class ReplyDraftTests(unittest.TestCase):
    def test_low_signal_comment_does_not_generate_draft(self) -> None:
        intake = prepare_reply_intake("comment-1", "666")

        draft = build_reply_draft(intake)

        self.assertIsNone(draft)

    def test_meaningful_comment_generates_conservative_draft(self) -> None:
        intake = prepare_reply_intake("comment-2", "这篇文章为什么这样设计？")

        draft = build_reply_draft(intake)

        self.assertIsInstance(draft, ReplyDraft)
        self.assertEqual(draft.comment_id, "comment-2")
        self.assertEqual(draft.version, 1)
        self.assertIn("谢谢你的问题", draft.text)
        self.assertIn("这篇文章为什么这样设计？", draft.text)


if __name__ == "__main__":
    unittest.main()
