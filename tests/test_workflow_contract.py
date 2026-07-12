import unittest
from pathlib import Path


WORKFLOW_ROOT = Path(__file__).parents[1] / ".github" / "workflows"


class WorkflowContractTests(unittest.TestCase):
    def test_state_writers_share_non_canceling_concurrency(self) -> None:
        for name in ("publish.yml", "reply-monitor.yml", "reply-dispatch.yml"):
            text = (WORKFLOW_ROOT / name).read_text(encoding="utf-8")
            self.assertIn("group: thread-os-state-write", text)
            self.assertIn("cancel-in-progress: false", text)

    def test_publish_workflow_uses_queue_and_content_secret(self) -> None:
        text = (WORKFLOW_ROOT / "publish.yml").read_text(encoding="utf-8")
        self.assertIn("repository: ${{ vars.CONTENT_REPO }}", text)
        self.assertIn("token: ${{ secrets.CONTENT_REPO_TOKEN }}", text)
        self.assertIn("content-repo/posts/queue", text)

    def test_reply_dispatch_exposes_explicit_dry_run_switch(self) -> None:
        text = (WORKFLOW_ROOT / "reply-dispatch.yml").read_text(encoding="utf-8")
        self.assertIn("REPLY_DRY_RUN", text)
        self.assertIn("CLIENT_PAYLOAD_JSON", text)

    def test_state_writers_upload_recovery_artifacts_on_failure(self) -> None:
        for name in ("publish.yml", "reply-monitor.yml", "reply-dispatch.yml"):
            text = (WORKFLOW_ROOT / name).read_text(encoding="utf-8")
            self.assertIn("actions/upload-artifact@v4", text)
            self.assertIn("if: failure()", text)


if __name__ == "__main__":
    unittest.main()
