import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkflowContractTests(unittest.TestCase):
    def test_all_json_writers_share_one_concurrency_group(self) -> None:
        for name in ("publish.yml", "reply-monitor.yml", "reply-dispatch.yml"):
            workflow = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
            self.assertIn("group: thread-os-state-write", workflow, name)

    def test_publish_workflow_checks_out_feed_read_only_and_uses_shared_cli(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "publish.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("repository: ${{ vars.CONTENT_REPO }}", workflow)
        self.assertIn("token: ${{ secrets.CONTENT_REPO_TOKEN }}", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("sparse-checkout: posts/queue", workflow)
        self.assertIn("--scheduled", workflow)
        self.assertIn('--content-id "$CONTENT_ID"', workflow)
        self.assertIn("- name: Commit publish task state\n        if: always()", workflow)


if __name__ == "__main__":
    unittest.main()
