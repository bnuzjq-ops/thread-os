import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from threads_bot_system.publish_feed import select_manual_source, select_scheduled_source


def _write_post(
    queue_dir: Path,
    content_id: str,
    *,
    scheduled_time: str | None = None,
) -> Path:
    schedule_line = f"scheduled_time: {scheduled_time}\n" if scheduled_time else ""
    path = queue_dir / f"{content_id}.md"
    path.write_text(
        "---\n"
        f"content_id: {content_id}\n"
        "platform: threads\n"
        "editorial_status: ready\n"
        f"{schedule_line}"
        "source_ref: test-fixture\n"
        "content_version: 1\n"
        "exported_at: 2026-07-12T10:00:00+08:00\n"
        "---\n\n"
        f"Body for {content_id}\n",
        encoding="utf-8",
    )
    return path


class PublishFeedTests(unittest.TestCase):
    def test_manual_selection_requires_explicit_content_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir)
            _write_post(queue_dir, "manual-1")

            selected = select_manual_source(queue_dir, "manual-1")

            self.assertEqual(selected.content_id, "manual-1")

    def test_scheduled_selection_skips_unscheduled_and_future_posts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir)
            _write_post(queue_dir, "manual-only")
            _write_post(queue_dir, "future", scheduled_time="2026-07-13T00:00:00Z")
            _write_post(queue_dir, "due-later", scheduled_time="2026-07-12T08:00:00Z")
            _write_post(queue_dir, "due-first", scheduled_time="2026-07-12T07:00:00Z")

            selected = select_scheduled_source(
                queue_dir,
                now=datetime(2026, 7, 12, 9, 0, tzinfo=timezone.utc),
            )

            self.assertIsNotNone(selected)
            self.assertEqual(selected.content_id, "due-first")

    def test_scheduled_selection_returns_none_when_only_unscheduled_posts_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir)
            _write_post(queue_dir, "manual-only")

            selected = select_scheduled_source(
                queue_dir,
                now=datetime(2026, 7, 12, 9, 0, tzinfo=timezone.utc),
            )

            self.assertIsNone(selected)

    def test_scheduled_selection_rejects_time_without_timezone(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir)
            _write_post(queue_dir, "bad-time", scheduled_time="2026-07-12T08:00:00")

            with self.assertRaisesRegex(ValueError, "timezone"):
                select_scheduled_source(
                    queue_dir,
                    now=datetime(2026, 7, 12, 9, 0, tzinfo=timezone.utc),
                )


if __name__ == "__main__":
    unittest.main()
