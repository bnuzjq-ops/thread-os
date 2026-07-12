# Acceptance Status

This document records verified evidence only. `PASS` requires a runtime or test artifact.

## Publish Lane

| Item | Status | Evidence |
| --- | --- | --- |
| Obsidian draft export | PASS | `scripts/export-threads-post.ps1`; exported `threads-codex-123` |
| Content repository checkout | PASS | GitHub Actions `Checkout content repository` succeeded |
| Queue contract | PASS | `posts/queue/`; `platform: threads`; `editorial_status: ready` |
| README/contract files excluded | PASS | Workflow scans only `content-repo/posts/queue` |
| Threads two-step publish | PASS | `threads-codex-123` produced post `18060289736735869` |
| Real Threads visibility | PASS | https://www.threads.com/@jq.sifu/post/DasjI8XETAR |
| JSON state writeback | PASS | `state/publish_tasks.json`, status `published`, post ID recorded |
| Future scheduled content is skipped | PASS | `tests/test_publish_runtime.py` |
| Permalink lookup failure avoids republish | PASS | `tests/test_publish_runtime.py` |
| Continuous multi-cycle real publish | NOT TESTED | Requires additional distinct test posts |
| Failure/unknown external alert delivery | NOT TESTED | GitHub step summary exists; end-user notification not verified |

## Reply Lane

| Item | Status | Evidence |
| --- | --- | --- |
| Real Threads comment monitor | PASS | Workflow run `29196998480`; real scan returned `comments: 0` and committed cursor/state |
| DeepSeek draft generation | NOT TESTED | No production comment run |
| Feishu review card | NOT TESTED | No production card acceptance |
| Feishu callback and GitHub dispatch | NOT TESTED | No production button click acceptance |
| Real Threads reply | NOT TESTED | No end-to-end reply ID/permalink |

## Current Boundary

- Runtime state remains in `thread-os/state/`.
- The content repository stores editorial snapshots only.
- Publishing does not rewrite the Obsidian source Markdown.
- `unknown` and `published` tasks are not automatically retried.
