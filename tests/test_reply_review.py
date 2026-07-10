import unittest

from threads_bot_system.reply_draft import build_reply_draft
from threads_bot_system.reply_flow import prepare_reply_intake
from threads_bot_system.reply_review import ReplyReviewPacket, build_reply_review_packet


class ReplyReviewTests(unittest.TestCase):
    def test_low_signal_comment_does_not_build_review_packet(self) -> None:
        intake = prepare_reply_intake("comment-1", "666")
        draft = build_reply_draft(intake)

        packet = build_reply_review_packet(intake, draft)

        self.assertIsNone(packet)

    def test_meaningful_comment_builds_review_packet(self) -> None:
        intake = prepare_reply_intake("comment-2", "这篇文章为什么这样设计？")
        draft = build_reply_draft(intake)

        packet = build_reply_review_packet(intake, draft)

        self.assertIsInstance(packet, ReplyReviewPacket)
        self.assertEqual(packet.comment_id, "comment-2")
        self.assertIn("回复审核", packet.title)
        self.assertIn("这篇文章为什么这样设计？", packet.body)
        self.assertIn(draft.text, packet.body)


if __name__ == "__main__":
    unittest.main()
