import tempfile
import unittest
from pathlib import Path

from threads_bot_system.export_feed import export_content


class ExportFeedTests(unittest.TestCase):
    def _write_source(
        self,
        ready_root: Path,
        *,
        content_id: str = "threads-test-001",
        platform: str = "threads",
        status: str = "ready",
        body: str = "Final [[topic|post]] body.",
    ) -> Path:
        ready_root.mkdir(parents=True, exist_ok=True)
        source = ready_root / "draft.md"
        source.write_text(
            "---\n"
            f"content_id: {content_id}\n"
            f"platform: {platform}\n"
            f"status: {status}\n"
            "source_ref: local-test\n"
            "private_notes: do not export\n"
            "---\n\n"
            f"{body}\n",
            encoding="utf-8",
        )
        return source

    def test_exports_ready_content_without_modifying_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ready_root = root / "30-Content" / "Threads" / "Ready"
            feed_repo = root / "feed"
            source = self._write_source(
                ready_root,
                body="Final [[topic|post]] body.\n\n%%internal note%%",
            )
            original = source.read_text(encoding="utf-8")

            result = export_content(
                source,
                feed_repo,
                ready_root=ready_root,
                exported_at="2026-07-12T17:30:00+08:00",
            )

            self.assertEqual(result.target_path, feed_repo / "posts" / "queue" / "threads-test-001.md")
            self.assertEqual(source.read_text(encoding="utf-8"), original)
            exported = result.target_path.read_text(encoding="utf-8")
            self.assertIn("editorial_status: ready", exported)
            self.assertIn("content_version: 1", exported)
            self.assertIn("exported_at: 2026-07-12T17:30:00+08:00", exported)
            self.assertIn("Final post body.", exported)
            self.assertNotIn("private_notes", exported)
            self.assertNotIn("internal note", exported)
            self.assertNotIn("[[", exported)

    def test_rejects_source_outside_ready_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ready_root = root / "30-Content" / "Threads" / "Ready"
            source = self._write_source(root / "30-Content" / "Threads" / "Drafts")

            with self.assertRaisesRegex(ValueError, "Ready"):
                export_content(source, root / "feed", ready_root=ready_root)

    def test_rejects_missing_content_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ready_root = root / "30-Content" / "Threads" / "Ready"
            source = self._write_source(ready_root, content_id="")

            with self.assertRaisesRegex(ValueError, "content_id"):
                export_content(source, root / "feed", ready_root=ready_root)

    def test_rejects_non_threads_platform(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ready_root = root / "30-Content" / "Threads" / "Ready"
            source = self._write_source(ready_root, platform="x")

            with self.assertRaisesRegex(ValueError, "threads"):
                export_content(source, root / "feed", ready_root=ready_root)

    def test_duplicate_content_id_requires_replace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ready_root = root / "30-Content" / "Threads" / "Ready"
            feed_repo = root / "feed"
            source = self._write_source(ready_root)
            export_content(source, feed_repo, ready_root=ready_root)

            with self.assertRaises(FileExistsError):
                export_content(source, feed_repo, ready_root=ready_root)

    def test_replace_increments_existing_content_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ready_root = root / "30-Content" / "Threads" / "Ready"
            feed_repo = root / "feed"
            source = self._write_source(ready_root)
            first = export_content(source, feed_repo, ready_root=ready_root)

            result = export_content(source, feed_repo, ready_root=ready_root, replace=True)

            self.assertEqual(first.content_version, 1)
            self.assertEqual(result.content_version, 2)
            self.assertIn("content_version: 2", result.target_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
