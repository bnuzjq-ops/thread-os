import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from threads_bot_system.cli import main


class FakeThreadsClient:
    def __init__(self, media_ids: list[str]) -> None:
        self.media_ids = media_ids

    def fetch_user_threads(self) -> list[str]:
        return self.media_ids


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

            def fake_run_publish(store, client, task_ids=None):
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

    def test_monitor_command_discovers_user_threads_when_no_media_id_is_given(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "reply_tasks.json"
            cursor_path = Path(tmpdir) / "reply_monitor_cursor.json"
            buffer = io.StringIO()
            fake_client = FakeThreadsClient(["media-1", "media-2"])
            fake_deepseek = object()
            captured: list[list[str]] = []

            def fake_run_reply_monitor(
                media_ids,
                threads_client,
                feishu_client,
                store_path,
                deepseek_client=None,
                cursor_path=None,
                dry_run=False,
                trigger_source="",
            ):
                captured.append(list(media_ids))
                return SimpleNamespace(comments=[], like_only_count=0, review_count=0, trigger_source="test")

            with patch("threads_bot_system.cli._build_threads_client", return_value=fake_client), patch(
                "threads_bot_system.cli._build_feishu_client", return_value=object()
            ), patch("threads_bot_system.cli._build_deepseek_client", return_value=fake_deepseek), patch(
                "threads_bot_system.cli.run_reply_monitor", side_effect=fake_run_reply_monitor
            ):
                with redirect_stdout(buffer):
                    exit_code = main([
                        "monitor",
                        "--store-path", str(store_path),
                        "--cursor-path", str(cursor_path),
                    ])

        self.assertEqual(exit_code, 0)
        self.assertEqual(captured[0], ["media-1", "media-2"])


if __name__ == "__main__":
    unittest.main()
