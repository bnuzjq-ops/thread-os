import unittest

from threads_bot_system.reply_monitor import CommentSnapshot, scan_comments


class ReplyMonitorTests(unittest.TestCase):
    def test_scan_comments_groups_like_only_and_review_comments(self) -> None:
        report = scan_comments(
            [
                CommentSnapshot(comment_id="comment-1", text="666"),
                CommentSnapshot(comment_id="comment-2", text="这篇文章为什么这样设计？"),
            ]
        )

        self.assertEqual(report.like_only_count, 1)
        self.assertEqual(report.review_count, 1)
        self.assertEqual([task.reply_task_id for task in report.review_tasks], ["reply:comment-2"])


if __name__ == "__main__":
    unittest.main()
