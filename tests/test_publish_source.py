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


if __name__ == "__main__":
    unittest.main()
