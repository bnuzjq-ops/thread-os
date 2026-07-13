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

## Completion Rule

Do not mark the whole system complete until every non-blocked acceptance item is `PASS`. Real reply acceptance may remain `BLOCKED` only with its cause and unblock condition recorded.
