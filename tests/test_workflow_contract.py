import unittest
from pathlib import Path


WORKFLOW_ROOT = Path(__file__).parents[1] / ".github" / "workflows"


class WorkflowContractTests(unittest.TestCase):
    def test_state_writers_share_non_canceling_concurrency(self) -> None:
        for name in ("publish.yml", "reply-monitor.yml", "reply-dispatch.yml"):
            text = (WORKFLOW_ROOT / name).read_text(encoding="utf-8")
            self.assertIn("group: thread-os-state-write", text)
            self.assertIn("cancel-in-progress: false", text)
            self.assertIn('git fetch origin "${BRANCH_NAME}"', text)
            self.assertIn('git rebase "origin/${BRANCH_NAME}"', text)

    def test_reply_state_writers_preserve_changes_before_rebase(self) -> None:
        for name in ("reply-monitor.yml", "reply-dispatch.yml"):
            text = (WORKFLOW_ROOT / name).read_text(encoding="utf-8")
            self.assertIn("git stash push --include-untracked", text)
            self.assertIn("git stash pop", text)

    def test_publish_state_writer_preserves_changes_before_rebase(self) -> None:
        text = (WORKFLOW_ROOT / "publish.yml").read_text(encoding="utf-8")
        self.assertIn('git stash push --include-untracked -m "publish-state"', text)
        self.assertIn("git stash pop", text)

    def test_publish_workflow_uses_queue_and_content_secret(self) -> None:
        text = (WORKFLOW_ROOT / "publish.yml").read_text(encoding="utf-8")
        self.assertIn("source_path:", text)
        self.assertIn("repository: ${{ vars.CONTENT_REPO }}", text)
        self.assertIn("token: ${{ secrets.CONTENT_REPO_TOKEN }}", text)
        self.assertIn("publish-feed/posts/queue/*.md", text)

    def test_publish_workflow_executes_a_batch_as_one_run(self) -> None:
        text = (WORKFLOW_ROOT / "publish.yml").read_text(encoding="utf-8")
        self.assertIn("PUBLISH_DISPATCH_TASKS", text)
        self.assertIn("batch_id", text)
        self.assertIn("while IFS= read -r task", text)
        self.assertIn("--source \"$source\"", text)

    def test_publish_workflow_maps_production_guard_variables(self) -> None:
        text = (WORKFLOW_ROOT / "publish.yml").read_text(encoding="utf-8")
        self.assertIn("ENV: ${{ vars.ENV }}", text)
        self.assertIn("PUBLISH_ENABLED: ${{ vars.PUBLISH_ENABLED }}", text)
        self.assertIn("DRY_RUN: ${{ vars.DRY_RUN }}", text)
        self.assertIn("MAX_DAILY_POSTS: ${{ vars.MAX_DAILY_POSTS || '10' }}", text)
        self.assertIn(
            "MIN_POST_INTERVAL_MINUTES: ${{ vars.MIN_POST_INTERVAL_MINUTES || '10' }}",
            text,
        )
        self.assertIn(
            "MAX_CONSECUTIVE_FAILURES: ${{ vars.MAX_CONSECUTIVE_FAILURES }}",
            text,
        )
        self.assertIn(
            "MAX_CONSECUTIVE_UNKNOWN: ${{ vars.MAX_CONSECUTIVE_UNKNOWN }}",
            text,
        )

    def test_publish_workflow_has_only_single_source_entrypoints(self) -> None:
        text = (WORKFLOW_ROOT / "publish.yml").read_text(encoding="utf-8")
        self.assertIn("repository_dispatch:", text)
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("\n  schedule:", text)
        self.assertNotIn('elif [ "$GITHUB_EVENT_NAME" = "schedule" ]', text)
        self.assertNotIn("for source in content-repo/publish-feed/posts/queue/*.md", text)
        source_input = text.split("source_path:", 1)[1].split("type: string", 1)[0]
        self.assertIn("required: true", source_input)

    def test_reply_dispatch_is_frozen_to_manual_dispatch(self) -> None:
        text = (WORKFLOW_ROOT / "reply-dispatch.yml").read_text(encoding="utf-8")
        self.assertIn("REPLY_DRY_RUN", text)
        self.assertIn("CLIENT_PAYLOAD_JSON", text)
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("repository_dispatch:", text)
        self.assertNotIn("types:", text)

    def test_reply_monitor_is_frozen_to_manual_dispatch(self) -> None:
        text = (WORKFLOW_ROOT / "reply-monitor.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("schedule:", text)
        self.assertNotIn("repository_dispatch:", text)
        self.assertNotIn("threads_reply_monitor", text)

    def test_state_writers_upload_recovery_artifacts_on_failure(self) -> None:
        for name in ("publish.yml", "reply-monitor.yml", "reply-dispatch.yml"):
            text = (WORKFLOW_ROOT / name).read_text(encoding="utf-8")
            self.assertIn("actions/upload-artifact@v4", text)
            self.assertIn("if: failure()", text)

    def test_failure_summaries_include_task_context(self) -> None:
        publish = (WORKFLOW_ROOT / "publish.yml").read_text(encoding="utf-8")
        self.assertIn("error_phase", publish)
        self.assertIn("recovery_action", publish)
        for name in ("reply-monitor.yml", "reply-dispatch.yml"):
            text = (WORKFLOW_ROOT / name).read_text(encoding="utf-8")
            self.assertIn("comment_id", text)
            self.assertIn("last_error", text)


if __name__ == "__main__":
    unittest.main()
