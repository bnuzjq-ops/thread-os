import unittest

from threads_bot_system.reply_card import ReplyCardPayload, build_reply_card
from threads_bot_system.reply_draft import build_reply_draft
from threads_bot_system.reply_flow import prepare_reply_intake
from threads_bot_system.reply_review import build_reply_review_packet


class ReplyCardTests(unittest.TestCase):
    def test_build_reply_card_uses_review_packet_content(self) -> None:
        intake = prepare_reply_intake("comment-2", "这篇文章为什么这样设计？")
        draft = build_reply_draft(intake)
        packet = build_reply_review_packet(intake, draft)

        card = build_reply_card(packet)

        self.assertIsInstance(card, ReplyCardPayload)
        self.assertEqual(card.title, packet.title)
        self.assertIn(packet.body, card.body)
        self.assertEqual([action.value for action in card.actions], [
            "send:reply:comment-2",
            "rewrite:reply:comment-2",
            "skip:reply:comment-2",
            "status:reply:comment-2",
        ])


if __name__ == "__main__":
    unittest.main()
