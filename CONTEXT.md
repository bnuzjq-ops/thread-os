# Current Context

## Repository Boundaries

- `C:\jq\OBS\Threads`: local Obsidian content production.
- `bnuzjq-ops/threads-publish-feed`: approved publication snapshots only.
- `bnuzjq-ops/thread-os`: code, workflows, tests, and JSON runtime state.
- Feishu Callback Worker only verifies and forwards actions.
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

- Remote `main` and local development branch are both `db17bc8`; worktree is clean.
- Python tests: 85 passed. Worker tests: 8 passed.
- Worker health is HTTP 200. Current deployment is Cloudflare version `3417252a-4860-4673-bc6a-69d3801fef43`, deployed from clean commit `198dcee`; Cloudflare provides no git SHA metadata.
- `rewrite` now persists comment text, calls DeepSeek again, increments `draft_version`, and sends a new review card in code; live verification is still `NOT_TESTED`.
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

1. Read `FINAL-GOAL.md`, `ACCEPTANCE-CHECKLIST.md`, `docs/ACCEPTANCE_STATUS.md`, and `RUNBOOK.md`.
2. Keep `PASS`, `NOT_TESTED`, and `BLOCKED` evidence-based.
3. Never treat mock or dry-run output as real Threads success.
4. Never retry `published`, `unknown`, `sent`, or `sending` tasks automatically.
5. Do not modify Secrets or trigger real external actions without explicit approval.
