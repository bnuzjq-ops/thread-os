import unittest

from threads_bot_system.reply_action import (
    mark_awaiting_review,
    mark_drafted,
    mark_failed,
    mark_rewrite_requested,
    mark_sent,
    mark_skipped,
)
from threads_bot_system.reply_task import ReplyTaskStatus, new_reply_task


class ReplyActionTests(unittest.TestCase):
    def test_mark_drafted_sets_draft_status_and_body(self) -> None:
        task = new_reply_task("comment-1")

        updated = mark_drafted(task, "draft text")

        self.assertEqual(updated.status, ReplyTaskStatus.DRAFTED)
        self.assertEqual(updated.draft, "draft text")
        self.assertEqual(updated.draft_version, 1)

    def test_mark_awaiting_review_attaches_feishu_message_id(self) -> None:
        task = mark_drafted(new_reply_task("comment-1"), "draft text")

        updated = mark_awaiting_review(task, "msg-1")

        self.assertEqual(updated.status, ReplyTaskStatus.AWAITING_REVIEW)
        self.assertEqual(updated.feishu_message_id, "msg-1")

    def test_mark_sent_sets_reply_id(self) -> None:
        task = mark_awaiting_review(mark_drafted(new_reply_task("comment-1"), "draft text"), "msg-1")

        updated = mark_sent(task, "reply-1")

        self.assertEqual(updated.status, ReplyTaskStatus.SENT)
        self.assertEqual(updated.reply_id, "reply-1")

    def test_mark_failed_records_error(self) -> None:
        task = new_reply_task("comment-1")

        updated = mark_failed(task, "boom")

        self.assertEqual(updated.status, ReplyTaskStatus.FAILED)
        self.assertEqual(updated.last_error, "boom")

    def test_mark_skipped_sets_skipped_status(self) -> None:
        task = new_reply_task("comment-1")

        updated = mark_skipped(task, "low value")

        self.assertEqual(updated.status, ReplyTaskStatus.SKIPPED)
        self.assertEqual(updated.last_error, "low value")

    def test_mark_rewrite_requested_keeps_draft_flow_open(self) -> None:
        task = mark_drafted(new_reply_task("comment-1"), "draft text")

        updated = mark_rewrite_requested(task, "rewrite_requested")

        self.assertEqual(updated.status, ReplyTaskStatus.DRAFTED)
        self.assertEqual(updated.last_error, "rewrite_requested")


if __name__ == "__main__":
    unittest.main()
