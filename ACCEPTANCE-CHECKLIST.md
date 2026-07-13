# Acceptance Checklist

Allowed statuses: `PASS`, `FAIL`, `BLOCKED`, `NOT_TESTED`.

## Current Summary

| Area | Status | Evidence or blocker |
| --- | --- | --- |
| Group A — Auto-trigger | NOT_TESTED | GitHub schedule is active; independent Cloudflare scheduler is implemented and tested but its Cron is not enabled yet |
| Group B — JSON concurrency & idempotency | PASS | 12/12 code review pass; shared concurrency group; claim-once; stale-version reject; terminal states not retried |
| Group C — Publish real acceptance | NOT_TESTED | Code review items are covered; C9 (3 continuous real posts) needs current-baseline human execution |
| Group D — Comment monitor | PASS | 10/10 code review pass; pagination; dedup; self-reply filter; untrusted-input segregation |
| Group E — DeepSeek draft | PASS | 9/9 pass after fixes; max_draft_chars truncation; no template fallback; 401/403 alerts |
| Group F — Feishu review & Worker | PASS | 12/12 code review pass; 4 button payloads correct; signature verification; Worker pure relay |
| Group G — Real Threads reply | NOT_TESTED | 1/3 verified (reply_id 17988946037829563); final gate requires 2 more distinct real comments |
| Group H — Error alerts | PASS | 8/8 alert paths pass; reply failure summary format aligned with publish workflow |
| Group I — Recovery | PASS | RUNBOOK covers failed/unknown/publishing/sending recovery, JSON backfill, token rotation, git conflicts |
| Group J — Cloudflare maintenance | PASS | Worker name, route, secrets, wrangler command documented; Cloudflare account info recorded |
| Group K — Security | PASS | 9/9 pass; no secrets in git; no auth header logging; minimal token permissions; untrusted input rules |
| Group L — Modularity | PASS | 13/13 pass; 84/84 Python tests pass; 7/7 Worker tests pass; single scheduler |
| Group M — Documentation | PASS | 12/12 pass; README updated; RUNBOOK expanded; FINAL-GOAL scheduler discipline; all docs aligned |
| Group N — Operational loop | BLOCKED | Requires C9 and G completion before 48h continuous run |

## Live Evidence Override 2026-07-13

- All code-level fixes pushed to `bnuzjq-ops/thread-os` main branch (`fd13947` and earlier).
- Reply Monitor workflow `311104281`: schedule (31 runs), workflow_dispatch, and repository_dispatch all active.
- Real publish: `platform_post_id: 18060289736735869` (https://www.threads.com/@jq.sifu/post/DasjI8XETAR).
- Real reply: `reply_id: 17988946037829563`, workflow `29227348273`.
- Live Feishu card and skip callback: runs `29223845054`, `29226259880`, `29226261576`, `29226273680`.
- 84/84 Python tests pass; 7/7 Worker tests pass.

## Rules

- No item may be `PASS` without evidence.
- `BLOCKED` does not mean `FAIL` and does not pause unrelated development.
- A real publish or reply must never be repeated solely because state writeback or permalink lookup failed.
- Mock and dry-run evidence must not be described as real platform success.
