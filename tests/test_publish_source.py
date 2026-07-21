import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from threads_bot_system.publish_source import load_publish_source
from threads_bot_system.publish_source import select_due_source, find_duplicate_scheduled_times


class PublishSourceTests(unittest.TestCase):
    def test_select_due_source_rejects_naive_now(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(ValueError, "now must include a timezone"):
                select_due_source(tmpdir, now=datetime(2026, 7, 12, 12, 0, 0))

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
            self.assertEqual(source.content_version, 1)

    def test_load_publish_source_reads_content_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "post.md"
            path.write_text(
                "---\ncontent_id: content-1\ncontent_version: 3\nplatform: threads\n"
                "status: ready\n---\n\nHello Threads\n",
                encoding="utf-8",
            )

            source = load_publish_source(path)

            self.assertEqual(source.content_version, 3)

    def test_load_publish_source_rejects_non_ready_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "post.md"
            path.write_text(
                "---\ncontent_id: content-1\nplatform: threads\nstatus: draft\n---\n\nHello Threads\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_publish_source(path)

    def test_load_publish_source_accepts_editorial_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "post.md"
            path.write_text(
                "---\ncontent_id: content-2\nplatform: threads\neditorial_status: ready\n"
                "scheduled_time: 2099-01-01T00:00:00+00:00\n---\n\nHello Threads\n",
                encoding="utf-8",
            )

            source = load_publish_source(path)

            self.assertEqual(source.status, "ready")
            self.assertEqual(source.scheduled_time, "2099-01-01T00:00:00+00:00")

    def test_scheduled_time_requires_timezone(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "post.md"
            path.write_text(
                "---\ncontent_id: content-3\nplatform: threads\neditorial_status: ready\n"
                "scheduled_time: 2099-01-01T00:00:00\n---\n\nHello\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_publish_source(path)

    def test_select_due_source_blocks_duplicate_times(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for content_id in ("b", "a"):
                (root / f"{content_id}.md").write_text(
                    f"---\ncontent_id: {content_id}\nplatform: threads\n"
                    "editorial_status: ready\nscheduled_time: 2020-01-01T00:00:00+00:00\n"
                    "---\n\nHello\n",
                    encoding="utf-8",
                )
            with self.assertRaisesRegex(ValueError, "duplicate scheduled_time"):
                select_due_source(root)

    def test_find_duplicate_scheduled_times(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for content_id in ("a", "b"):
                (root / f"{content_id}.md").write_text(
                    f"---\ncontent_id: {content_id}\nplatform: threads\n"
                    "editorial_status: ready\nscheduled_time: 2026-07-20T22:00:00+08:00\n"
                    "---\n\nHello Threads\n",
                    encoding="utf-8",
                )
            self.assertEqual(
                find_duplicate_scheduled_times(root),
                {"2026-07-20T22:00:00+08:00": ["a", "b"]},
            )


if __name__ == "__main__":
    unittest.main()
