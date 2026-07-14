# Current Context

> **Latest baseline: 2026-07-14.** This section supersedes older dated
> overrides below. Older entries are historical evidence only.

## Current Truth

- Execution repository: `bnuzjq-ops/thread-os`, remote `main` includes the
  latest permalink-auth fix (`6e4786c` after rebase).
- Content source repository: `bnuzjq-ops/threads-content-library`.
- Publish snapshot repository: `bnuzjq-ops/threads-publish-feed`.
- The execution workflow reads `CONTENT_REPO = bnuzjq-ops/threads-publish-feed`;
  it does not read the content library directly.
- The content export workflow is the bridge from the content library to the
  publish snapshot repository.

## Real Publish Evidence

- Direct GitHub-only `123` test reached Threads and published successfully.
- Full content-library `1234` test passed end to end:
  content library -> export workflow -> publish snapshot -> publish workflow
  -> Threads.
- Content export run: `29320765520`.
- Publish run: `29320802183`.
- Real post: `https://www.threads.com/@jq.sifu/post/DaxI7uam9Um`.
- `platform_post_id`: `18201324496321542`.
- Remote state recorded `status=published`, `platform_post_id`, and a valid
  permalink.
- The temporary `1234` source file and publish snapshot were removed after
  verification. The real Threads post remains as evidence.

## Root Cause Found And Fixed

- The earlier `Media Not Found` runs occurred before the current Token state
  was working; they are terminal historical failures and must not be retried.
- A separate bug made permalink lookup omit `access_token`. The fix is in
  `threads_bot_system/threads_api.py` and is covered by tests.
- Publish correlation diagnostics now log only user ID, endpoints, and a
  redacted creation ID. Tokens are never logged.
- Current test result after the fix: `101 tests passed`.

## Current Acceptance Boundary

- Content library -> publish snapshot: **PASS**.
- Publish snapshot -> GitHub Actions -> Threads: **PASS**.
- Real Threads publish and permalink persistence: **PASS** for the `1234`
  evidence post.
- Scheduled automatic publishing: **NOT_TESTED as a full online cycle**;
  manual dispatch was used for the end-to-end proof.
- Automatic reply triggers remain frozen by design. Reply code and manual
  entry points are retained, but no automatic monitor/scheduler should be
  re-enabled without an explicit decision.
- Real reply acceptance remains **BLOCKED** until a fresh unprocessed real
  comment is available and the frozen reply flow is intentionally resumed.

## Menu Exit Override (2026-07-13)

- Current remote `main` is `e59559a`; local branch is aligned with `origin/main` and the worktree is clean.
- The current Feishu menu route is `application.bot.menu_v6` -> `threads-reply-worker` -> `repository_dispatch` (`threads_reply_action`) -> `Reply Dispatch` -> CLI.
- Worker menu forwarding is deployed in the existing Worker; no second Worker was created.
- `Reply Dispatch` YAML was fixed at `da60ddd`; the previous `push` workflow-file failures had no jobs and were caused by invalid YAML, not a menu event.
- CLI menu handlers now cover `system_health`, `review_next`, `action_rewrite`, `action_skip`, and `action_send`.
- `operator_state.json` persists per-user active task selection and processed menu `event_id` values for idempotency.
- Local evidence: Python tests `98 passed`; Worker tests `9 passed`; reply-dispatch YAML parses successfully.
- Online menu end-to-end evidence is still `NOT_TESTED`: no new `application.bot.menu_v6` GitHub run has been observed.
- Required first external verification: click Feishu `审核 -> 系统状态`; this is read-only and must return an ordinary private message.
- Do not treat Worker `/health` or a green code test as proof of the menu exit chain.

## Repository Boundaries

- `D:\Obsidian`: personal knowledge vault.
- `D:\Obsidian\Work\Content Library`: formal content source of truth.
- `bnuzjq-ops/threads-publish-feed`: approved/scheduled publication snapshots only.
- `bnuzjq-ops/thread-os`: code, workflows, tests, and JSON runtime state.
- Auto-reply is frozen; Feishu/Worker reply entry points are preserved but not part of active automation.
- D1 is deferred; JSON is the current runtime state backend.

## Verified Publish Capability

- Obsidian export tool writes only `posts/queue/<content_id>.md`.
- Queue contract uses `platform: threads` and `editorial_status: ready`.
- Scheduled selection requires timezone-aware ISO 8601 and compares in UTC.
- Threads publishing uses the two-step container plus `creation_id` flow.
- A real post was verified at:
  `https://www.threads.com/@jq.sifu/post/DasjI8XETAR`
- Runtime state records post ID, permalink, timestamps, error type, and recovery context.

## Verified Reply Code Capability

- Reply monitor has run against the real Threads API and returned `comments: 0`.
- DeepSeek independent verification passed in Workflow run `29197690303`.
- Reply state claim, draft version, Worker signature, and dry-run guards have local tests.
- Python tests: 67 passed. Worker Node tests: 5 passed.

## Current Acceptance Boundary

## Current Baseline Override (2026-07-13)

- Remote `main` is `ac18fb5`; the local verification branch contains no uncommitted changes and is aligned with `origin/main`.
- Python tests: 91 passed. Worker and scheduler tests: 10 passed. Latest natural monitor run `29252755865` completed successfully.
- Worker health is HTTP 200. Current callback deployment is Cloudflare version `4f90ee89-8c39-4d8b-95c1-ac72ca92829c`, deployed from the trace and stale-card-protection callback code; Cloudflare provides no git SHA metadata.
- `rewrite` persists comment text, calls DeepSeek again, increments `draft_version`, and updates the original review card while preserving its actions; live fresh-card verification remains NOT_TESTED.
- Monitor state writeback fix is proven by natural run `29250464850` and remote state commit `255613a`.
- The last live `send` failed with Threads `Media Not Found`; do not retry that terminal task.
- A fresh comment is required to verify the current `send`, `rewrite`, `skip`, and `status` paths.

- Live Feishu/dispatch dry-run: `NOT_TESTED`; it sends a real Feishu test receipt.
- Continuous three-post real acceptance: `NOT_TESTED`; it requires real Threads publishing.
- Real reply end to end: `BLOCKED` by `no_new_real_comment`.

## Current Evidence Override (2026-07-13)

- A real comment produced a DeepSeek draft and Feishu review card.
- Feishu `skip` was accepted by the live Worker and dispatched to GitHub successfully; the task is terminal `skipped`.
- Real reply and live dry-run remain unverified because the skipped task cannot be reused; a new comment must create a fresh task.
- Do not rerun empty comment monitors waiting for data.

## Continuation Rules

## Latest-Baseline Execution Principle

- Always use the latest valid remote `main` and the currently deployed platform version as the implementation baseline.
- Older local branches, squash predecessors, and historical patches are reference only and must not block forward progress.
- Do not wait for manual review to continue non-blocked implementation, testing, documentation, or runtime diagnosis.
- When a real external action is required, continue every safe adjacent task and record the external item as `NOT_TESTED` or `BLOCKED` rather than pausing the overall objective.

1. Read `FINAL-GOAL.md`, `ACCEPTANCE-CHECKLIST.md`, `docs/ACCEPTANCE_STATUS.md`, and `RUNBOOK.md`.
2. Keep `PASS`, `NOT_TESTED`, and `BLOCKED` evidence-based.
3. Never treat mock or dry-run output as real Threads success.
4. Never retry `published`, `unknown`, `sent`, or `sending` tasks automatically.
5. Do not modify Secrets or trigger real external actions without explicit approval.
