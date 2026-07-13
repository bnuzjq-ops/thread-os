# Restart Handoff

## Start Here

Read, in order:

1. `FINAL-GOAL.md`
2. `ACCEPTANCE-CHECKLIST.md`
3. `docs/ACCEPTANCE_STATUS.md`
4. `RUNBOOK.md`
5. `CONTEXT.md`

## Current Remote

- Execution repository: `bnuzjq-ops/thread-os`
- Content repository: `bnuzjq-ops/threads-publish-feed`
- Runtime state: `state/publish_tasks.json`, `state/reply_tasks.json`
- Shared state concurrency group: `thread-os-state-write`

## Do Not Repeat

- Do not rescan old repositories or the whole Obsidian vault.
- Do not add `THREADS_MEDIA_IDS` back into the publish design.
- Do not rerun empty Reply Monitor scans solely to wait for comments.
- Do not publish or reply again when state is `published`, `unknown`, `sent`, or `sending`.

## Remaining External Actions

- Live Feishu/dispatch dry-run needs explicit approval because it sends a real Feishu receipt.
- Three-post real publish acceptance needs explicit approval because it creates real Threads posts.
- Real reply acceptance is blocked until a new unprocessed comment exists.

## Evidence

- Real publish: `https://www.threads.com/@jq.sifu/post/DasjI8XETAR`
- DeepSeek verification: GitHub Actions run `29197690303`
- Real monitor scan: GitHub Actions run `29197058923`, `comments: 0`
