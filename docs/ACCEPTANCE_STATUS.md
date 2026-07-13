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
| Feishu review card | PASS | Live review card run `29223845054`; persisted `feishu_message_id` |
| Feishu callback and GitHub dispatch | PASS (skip path) | Live runs `29226259880`, `29226261576`, `29226273680` |
| Real Threads reply | BLOCKED | New real comment and controlled `send` are still required |

## Current Boundary

## Live Audit 2026-07-13

- Feishu review card: PASS. Run `29223845054` created a real review card; task `reply:18080707790256878` is `awaiting_review` with a saved `feishu_message_id`.
- DeepSeek independent draft: PASS. The same task contains a generated draft and has not been sent to Threads.
- Feishu callback and GitHub dispatch: PASS for `skip`. The live callback now reaches GitHub dispatch; the earlier `200671` was caused by stale/missing Worker configuration and is retained only as historical evidence.
- Real Threads reply: BLOCKED. The task has no `reply_id`;解除条件是完成 Worker Secret 配置后点击一次 `send`，并观察 `reply-dispatch`、Threads 回复和状态回写。
- Local verification: PASS. Python tests: 83; Worker tests: 6.
- Latest live callback verification: PASS. Runs `29226259880`, `29226261576`, and `29226273680` completed successfully; the task reached `skipped` with `last_error=skip_requested`, proving Feishu -> Worker -> GitHub dispatch -> reply state handling. No Threads reply was attempted.
- Safe reply dry-run entry: PASS (code). `reply-monitor.yml` now accepts a manual `dry_run` input, persists the flag on new tasks, and dispatch enforces the persisted flag before any Threads call; tests cover the path. Live dry-run receipt remains NOT_TESTED.

## Latest Live Evidence

### Status Overrides

- `Feishu review card`: PASS, evidenced by run `29223845054` and saved `feishu_message_id`.
- `Feishu callback and GitHub dispatch`: PASS for `skip`, evidenced by runs `29226259880`, `29226261576`, and `29226273680`.
- `Real Threads reply`: BLOCKED pending a new task and one controlled `send`; the skipped task must not be reused.

- Feishu review card: PASS. GitHub Actions run `29223845054` reached success; task `reply:18080707790256878` is `awaiting_review` and has a saved Feishu message ID.
- Feishu callback and GitHub dispatch: PASS for the live `skip` action; runs
  `29226259880`, `29226261576`, and `29226273680` accepted the callback and
  completed the dispatch without calling Threads.

- Runtime state remains in `thread-os/state/`.
- The content repository stores editorial snapshots only.
- Publishing does not rewrite the Obsidian source Markdown.
- `unknown` and `published` tasks are not automatically retried.

## Live Reply Recheck (2026-07-13)

- Reply API two-step contract: **PASS**. Commit `9a25524` creates a text
  container with `reply_to_id`, then publishes it with `creation_id`; the
  focused and full Python test suites passed (82 tests).
- Reply Monitor after the fix: **PASS**. Workflow run `29227004783` ran the
  code from `9a25524` successfully and found no new comments.
- Real Threads reply: **BLOCKED** (`no_new_real_comment`). The previous
  failed task used the pre-fix implementation and remains terminal; it is not
  retried automatically.解除条件：出现一条新的、尚未处理的真实评论。
- Real reply end-to-end acceptance: **BLOCKED**, not PASS or FAIL. It still
  requires a new comment, a Feishu `send` click, a successful dispatch, a
  Threads `reply_id`, and the final Feishu receipt.
