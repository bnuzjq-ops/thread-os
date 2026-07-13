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
| Scheduled time requires timezone | PASS | `tests/test_publish_source.py` |
| Scheduler reference time requires timezone | PASS | `tests/test_publish_source.py`; naive `now` is rejected before UTC comparison |
| Due source selection is stable | PASS | `tests/test_publish_source.py`; UTC comparison and `content_id` tie-break |
| Scheduled run publishes at most one source | PASS | `select-scheduled-source` CLI and `publish.yml` |
| Publish state records transition timestamps | PASS | `tests/test_publish_store.py`; `created_at`, `claimed_at`, `updated_at` |
| Publish errors contain recovery context | PASS | `tests/test_publish_runtime.py`; type, phase, external action, retry policy |
| Corrupt JSON fails closed | PASS | `tests/test_publish_store.py`; invalid state raises before task/API execution |
| Repository and Git history contain no detected Secrets | PASS | Targeted tracked-file and history pattern scan; no values printed |
| Failure alerts include actionable task context | PASS | Workflow summaries include task ID, phase/status, error, action and recovery fields |
| Publish error classification coverage | PASS | `tests/test_threads_api.py`; HTTP auth/permission, network timeout, and invalid JSON paths preserve actionable error context |
| Workflow state/concurrency contract | PASS | `tests/test_workflow_contract.py`; shared group, queue boundary, and dry-run switch |
| State write failure preserves recovery artifact | PASS | `tests/test_workflow_contract.py`; failure paths upload state JSON for recovery |
| Permalink lookup failure avoids republish | PASS | `tests/test_publish_runtime.py` |
| Continuous multi-cycle real publish | NOT TESTED | Requires additional distinct test posts |
| Failure/unknown external alert delivery | NOT TESTED | GitHub step summary exists; end-user notification not verified |

## Reply Lane

| Item | Status | Evidence |
| --- | --- | --- |
| Real Threads comment monitor | PASS | Workflow run `29196998480`; real scan returned `comments: 0` and committed cursor/state |
| DeepSeek independent API draft | PASS | Workflow run `29197690303`; fixed test comment returned a non-empty draft without Threads/Feishu calls |
| Reply dispatch dry-run guard | PASS | `tests/test_reply_runtime.py`; dry-run records test result and makes zero Threads calls |
| Worker dry-run propagation | PASS | `tests/reply_worker.test.mjs`; explicit `dry_run` is forwarded, default payload is unchanged |
| Live Feishu/dispatch dry-run | NOT_TESTED | Would send a real test receipt to Feishu; requires explicit external-action approval |
| Reply task idempotency and draft-version claim | PASS | `tests/test_task_store_contract.py`, `tests/test_reply_runtime.py` |
| Reply failed/unknown handling | PASS | `tests/test_reply_runtime.py`, `tests/test_task_store_contract.py` |
| DeepSeek failure and empty-output rejection | PASS | `tests/test_deepseek_api.py`, `tests/test_reply_runtime.py` |
| DeepSeek error classification coverage | PASS | `tests/test_deepseek_api.py`; HTTP auth failure, invalid JSON, and empty message content are rejected explicitly |
| Comment prompt-injection boundary | PASS | `DeepSeekClient` treats comment text as untrusted data; `tests/test_deepseek_api.py` verifies the system rule |
| Feishu card action contract | PASS | `tests/test_feishu_api.py`, `tests/test_reply_card.py` |
| Feishu HTTP error diagnostics | PASS | `tests/test_feishu_api.py`; HTTP error responses preserve the Feishu JSON body for configuration/permission diagnosis |
| Worker signature and callback contract | PASS | `tests/reply_worker.test.mjs` |
| State Worker atomic claim contract | PASS | `worker/state-service/test/index.test.mjs` |
| Feishu review card | NOT TESTED | No production card acceptance |
| Feishu callback and GitHub dispatch | NOT TESTED | No production button click acceptance |
| Real Threads reply | NOT TESTED | No end-to-end reply ID/permalink |

## Current Boundary

- Runtime state remains in `thread-os/state/`.
- The content repository stores editorial snapshots only.
- Publishing does not rewrite the Obsidian source Markdown.
- `unknown` and `published` tasks are not automatically retried.
