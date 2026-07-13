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
