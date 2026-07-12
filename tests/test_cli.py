import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from threads_bot_system.cli import main
from threads_bot_system.export_feed import ExportResult


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
            self.assertEqual(captured[0].get_task("threads:content-1").text, "Hello Threads")

    def test_export_content_command_writes_feed_without_push_by_default(self) -> None:
        result = ExportResult(
            content_id="content-1",
            target_path=Path("feed/posts/queue/content-1.md"),
            content_version=1,
        )
        with patch("threads_bot_system.cli.export_content", return_value=result) as export_mock, patch(
            "threads_bot_system.cli.push_export"
        ) as push_mock:
            exit_code = main(
                [
                    "export-content",
                    "--source",
                    "ready/content-1.md",
                    "--ready-root",
                    "ready",
                    "--feed-repo",
                    "feed",
                ]
            )

        self.assertEqual(exit_code, 0)
        export_mock.assert_called_once()
        push_mock.assert_not_called()

    def test_export_content_push_checks_repo_before_export_and_pushes_result(self) -> None:
        result = ExportResult(
            content_id="content-1",
            target_path=Path("feed/posts/queue/content-1.md"),
            content_version=1,
        )
        with patch("threads_bot_system.cli.ensure_feed_repo_clean") as clean_mock, patch(
            "threads_bot_system.cli.export_content", return_value=result
        ) as export_mock, patch("threads_bot_system.cli.push_export") as push_mock:
            exit_code = main(
                [
                    "export-content",
                    "--source",
                    "ready/content-1.md",
                    "--ready-root",
                    "ready",
                    "--feed-repo",
                    "feed",
                    "--push",
                ]
            )

        self.assertEqual(exit_code, 0)
        clean_mock.assert_called_once_with(Path("feed"))
        export_mock.assert_called_once()
        push_mock.assert_called_once_with(Path("feed"), result)

    def test_publish_feed_dry_run_does_not_build_client_or_write_state(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            queue_dir = root / "queue"
            queue_dir.mkdir()
            source_path = queue_dir / "content-1.md"
            source_path.write_text(
                "---\n"
                "content_id: content-1\n"
                "platform: threads\n"
                "editorial_status: ready\n"
                "content_version: 1\n"
                "---\n\n"
                "Hello Threads\n",
                encoding="utf-8",
            )
            store_path = root / "publish_tasks.json"
            buffer = io.StringIO()

            with patch(
                "threads_bot_system.cli._build_threads_client",
                side_effect=AssertionError("dry run must not build a Threads client"),
            ):
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "publish",
                            "--store-path",
                            str(store_path),
                            "--feed-dir",
                            str(queue_dir),
                            "--content-id",
                            "content-1",
                            "--dry-run",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        self.assertFalse(store_path.exists())
        self.assertIn('"content_id": "content-1"', buffer.getvalue())

    def test_monitor_command_discovers_user_threads_when_no_media_id_is_given(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "reply_tasks.json"
            buffer = io.StringIO()
            fake_client = FakeThreadsClient(["media-1", "media-2"])
            captured: list[list[str]] = []

            def fake_run_reply_monitor(media_ids, threads_client, feishu_client, store_path, deepseek_client=None):
                captured.append(list(media_ids))
                return SimpleNamespace(comments=[], like_only_count=0, review_count=0)

            with patch("threads_bot_system.cli._build_threads_client", return_value=fake_client), patch(
                "threads_bot_system.cli._build_feishu_client", return_value=object()
            ), patch("threads_bot_system.cli._build_deepseek_client", return_value=None), patch(
                "threads_bot_system.cli.run_reply_monitor", side_effect=fake_run_reply_monitor
            ):
                with redirect_stdout(buffer):
                    exit_code = main(["monitor", "--store-path", str(store_path)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(captured[0], ["media-1", "media-2"])


if __name__ == "__main__":
    unittest.main()
