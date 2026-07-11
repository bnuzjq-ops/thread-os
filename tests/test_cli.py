import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from threads_bot_system.cli import main


class CliTests(unittest.TestCase):
    def test_summary_command_prints_project_summary(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["summary"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Threads", buffer.getvalue())

    def test_publish_command_prints_publish_summary(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "publish_tasks.json"
            buffer = io.StringIO()
            with patch("threads_bot_system.cli._build_threads_client", return_value=object()), patch(
                "threads_bot_system.cli.run_publish",
                return_value=SimpleNamespace(attempted=1, posted=1),
            ):
                with redirect_stdout(buffer):
                    exit_code = main(["publish", "--store-path", str(store_path)])

        self.assertEqual(exit_code, 0)
        self.assertIn('"attempted": 1', buffer.getvalue())
        self.assertIn('"posted": 1', buffer.getvalue())

    def test_publish_command_loads_markdown_source_into_json_store(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "publish_tasks.json"
            source_path = Path(tmpdir) / "post.md"
            source_path.write_text(
                "---\ncontent_id: content-1\nplatform: threads\nstatus: ready\n---\n\nHello Threads\n",
                encoding="utf-8",
            )
            captured: list[object] = []

            def fake_run_publish(store, client):
                captured.append(store)
                return SimpleNamespace(attempted=0, posted=0)

            with patch("threads_bot_system.cli._build_threads_client", return_value=object()), patch(
                "threads_bot_system.cli.run_publish", side_effect=fake_run_publish
            ):
                exit_code = main(
                    ["publish", "--store-path", str(store_path), "--source", str(source_path)]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(captured[0].get_task("publish:content-1").text, "Hello Threads")


if __name__ == "__main__":
    unittest.main()
