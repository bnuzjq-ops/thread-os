import tempfile
import unittest
from pathlib import Path

from threads_bot_system.publish_source import load_publish_source


class PublishSourceTests(unittest.TestCase):
    def test_load_publish_source_reads_ready_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "post.md"
            path.write_text(
                "---\ncontent_id: content-1\nplatform: threads\nstatus: ready\n---\n\nHello Threads\n",
                encoding="utf-8",
            )

            source = load_publish_source(path)

            self.assertEqual(source.content_id, "content-1")
            self.assertEqual(source.text, "Hello Threads")

    def test_load_publish_source_rejects_non_ready_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "post.md"
            path.write_text(
                "---\ncontent_id: content-1\nplatform: threads\nstatus: draft\n---\n\nHello Threads\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_publish_source(path)

    def test_load_publish_source_reads_publish_feed_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "post.md"
            path.write_text(
                "---\n"
                "content_id: content-2\n"
                "platform: threads\n"
                "editorial_status: ready\n"
                "scheduled_time: 2026-07-20T02:00:00Z\n"
                "source_ref: local-test\n"
                "content_version: 1\n"
                "exported_at: 2026-07-12T17:30:00+08:00\n"
                "---\n\n"
                "Scheduled Threads post\n",
                encoding="utf-8",
            )

            source = load_publish_source(path)

            self.assertEqual(source.content_id, "content-2")
            self.assertEqual(source.status, "ready")
            self.assertEqual(source.scheduled_time, "2026-07-20T02:00:00Z")
            self.assertEqual(source.content_version, 1)


if __name__ == "__main__":
    unittest.main()
