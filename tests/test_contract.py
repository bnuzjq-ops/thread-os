import unittest
from pathlib import Path

from threads_bot_system.contract import (
    CONTENT_REPO_ROOT,
    EXECUTION_REPO_ROOT,
    LEGACY_REPO_ROOT,
    project_manifest,
    render_project_summary,
)


class ContractTests(unittest.TestCase):
    def test_manifest_has_expected_boundaries(self) -> None:
        manifest = project_manifest()

        self.assertEqual(manifest["project_name"], "Threads 自动化系统 V2")
        self.assertEqual(manifest["execution_repo_root"], str(EXECUTION_REPO_ROOT))
        self.assertEqual(manifest["content_repo_root"], str(CONTENT_REPO_ROOT))
        self.assertEqual(manifest["legacy_repo_root"], str(LEGACY_REPO_ROOT))
        self.assertEqual(EXECUTION_REPO_ROOT, Path(__file__).resolve().parents[1])

    def test_summary_mentions_two_chains(self) -> None:
        summary = render_project_summary()

        self.assertIn("发布链路:", summary)
        self.assertIn("回复链路:", summary)
        self.assertIn("Cloudflare Worker", summary)
        self.assertIn("GitHub dispatch", summary)


if __name__ == "__main__":
    unittest.main()
