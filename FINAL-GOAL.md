# Threads Automation Final Goal

## Scope

The system must run repeatable publish and semi-automatic reply cycles without duplicate external actions, silent failures, or unrecoverable state.

## Boundaries

- Obsidian produces and approves content.
- `threads-publish-feed` stores approved publication snapshots only.
- `thread-os` owns workflows, API clients, business state, tests, alerts, and recovery.
- Feishu review is mandatory before a real reply.
- D1, images, threads, and multi-platform publishing are out of the current scope.

## Current State

- Publish path: verified once end to end with a real Threads post.
- Reply monitor: real API scan verified; latest scans returned `comments: 0`.
- Reply code path: local tests and safe dry-run logic implemented.
- Real reply end to end: `BLOCKED` by `no_new_real_comment`.

## Scheduler Discipline

- GitHub Actions `schedule` is the single official V1 auto-trigger.
- Cloudflare Cron SHALL NOT be enabled while GitHub Schedule is active.
- If Cloudflare Cron becomes necessary:
  1. GitHub Schedule MUST be removed from `reply-monitor.yml` first.
  2. The change MUST be documented in `ACCEPTANCE-CHECKLIST.md`.
  3. Only one scheduler may be active at any time.
- Two concurrent schedulers is a FAIL condition for the system.

## Current Evidence Override (2026-07-13)

The external blocker is no longer comment discovery for the existing test task. Feishu card delivery and the live `skip` callback path are verified. Real `send` and live dry-run require a fresh comment/task because the existing task is terminal `skipped`.

## Completion Rule

Do not mark the whole system complete until every non-blocked acceptance item is `PASS`. Real reply acceptance may remain `BLOCKED` only with its cause and unblock condition recorded.
# 当前权威基线（2026-07-14）

当前实现以 `C:\jq\AI\Thread OS\THREADS_SYSTEM_HANDOFF.md` 为准：

- 执行仓库：`C:\jq\AI\Thread OS\Threads-bot system`
- 内容主库：`D:\Obsidian\Threads os`
- 远程内容仓库：`bnuzjq-ops/threads-content-library`
- 历史快照仓库：`bnuzjq-ops/threads-publish-feed`
- 自动回复冻结
