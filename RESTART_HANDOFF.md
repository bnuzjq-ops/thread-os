# Restart Handoff

> **Latest handoff baseline: 2026-07-14.** Read this section first. Older
> sections below are historical and may contain superseded run IDs or status.

## Current System Map

- `bnuzjq-ops/threads-content-library`: content system repository at
  `D:\Obsidian\Threads os`, containing source content and `publish-feed/` snapshots.
- `bnuzjq-ops/threads-publish-feed`: historical snapshot backup only; do not
  use it as the runtime source after migration.
- `bnuzjq-ops/thread-os`: execution code, GitHub Actions, and runtime state.
- The publish workflow reads `publish-feed/posts/queue` inside the content
  system repository through `CONTENT_REPO`.
- JSON remains the runtime state backend. D1 is deferred.

## Latest Verified Result

The full online publication chain is verified with content `1234`:

```text
threads-content-library
  -> Export workflow 29320765520
  -> threads-publish-feed
  -> Publish workflow 29320802183
  -> Threads post
```

- Post: `https://www.threads.com/@jq.sifu/post/DaxI7uam9Um`
- Platform ID: `18201324496321542`
- State: `published`
- Permalink: persisted successfully.
- Test source and snapshot were deleted after verification.

## Important Debugging Facts

- A green GitHub workflow is not enough; inspect `publish_tasks.json` and the
  real Threads post ID/permalink.
- Earlier `Media Not Found` failures were from the pre-fix Token/runtime
  state, not proof that the content library bridge was broken.
- The permalink bug was caused by a missing `access_token` in
  `get_post_permalink()`. It is fixed and tested.
- Do not republish tasks already marked `published`, `unknown`, `sent`, or
  `sending`. Historical failed tasks require manual diagnosis first.
- Do not add `THREADS_MEDIA_IDS` back into the design.

## Remaining Work

- Validate one scheduled online cycle separately from manual dispatch.
- Keep automatic reply workflows frozen unless explicitly resumed.
- If reply work resumes, use a fresh real comment and verify the complete
  Feishu -> Worker -> GitHub dispatch -> Threads -> state回写 chain.

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

## Current Baseline Override (2026-07-13)

- Current remote `main`: `db17bc8`; local worktree was clean at baseline.
- Current code tests: Python 85 passed; Worker 8 passed.
- Current Worker deployment is Cloudflare version `3417252a-4860-4673-bc6a-69d3801fef43`, deployed from clean commit `198dcee`; Cloudflare reports no git SHA metadata.
- `rewrite` has been implemented to regenerate a draft and send a new card; it needs a fresh live card for verification.
- The previous live `send` failed with `Media Not Found`; the old task must not be retried.

- Live Feishu/dispatch dry-run needs explicit approval because it sends a real Feishu receipt.
- Three-post real publish acceptance needs explicit approval because it creates real Threads posts.
- Real reply acceptance is blocked until a new unprocessed comment exists.

## Evidence

- Real publish: `https://www.threads.com/@jq.sifu/post/DasjI8XETAR`
- DeepSeek verification: GitHub Actions run `29197690303`
- Real monitor scan: GitHub Actions run `29197058923`, `comments: 0`

## Latest Runtime Evidence

- Real Feishu review card: verified by run `29223845054`.
- Feishu `skip` -> Worker -> GitHub dispatch: verified by runs `29226259880`, `29226261576`, `29226273680`.
- Do not reuse the terminal `skipped` task for `send`; wait for a fresh comment/task.
# Execution Principle

Use the latest valid remote `main` and deployed platform version as the source
of truth. Do not wait for manual review or external test input before
continuing non-blocked code, test, documentation, and diagnosis work. Record
external dependencies as `NOT_TESTED` or `BLOCKED` without pausing the rest of
the objective.
