# Auto-Reply System Frozen

Freeze date: 2026-07-14

## Scope

The legacy auto-reply chain is retained as code but removed from active external trigger paths:

Threads comments -> Reply Monitor -> DeepSeek -> Feishu -> Cloudflare Worker -> GitHub dispatch -> Threads reply

## Frozen Workflows

- `.github/workflows/reply-monitor.yml`
  - Removed `repository_dispatch: threads_reply_monitor`.
  - No `schedule` trigger is present.
  - Only `workflow_dispatch` remains.
  - Manual runs default to `dry_run: true`.
- `.github/workflows/reply-dispatch.yml`
  - Removed `repository_dispatch: threads_reply_action`.
  - Only `workflow_dispatch` remains.
  - Manual runs default to `dry_run: true`.

## Preserved Code

- `threads_bot_system` reply modules are kept for future recovery.
- Feishu and Worker code is not deleted.
- GitHub Secrets and historical state files are not removed.
- Publish workflow `.github/workflows/publish.yml` is unchanged and remains active for the content publishing chain.

## Evidence That Auto-Reply Cannot Run Proactively

- There is no reply workflow `schedule` trigger.
- Reply workflows no longer accept GitHub `repository_dispatch` events.
- Cloudflare Worker or Feishu callbacks cannot start reply GitHub Actions through the removed dispatch triggers.
- Manual reply workflow entry points default to dry-run.

## Manual Recovery Steps

1. Confirm the desired recovery target and current reply state.
2. Re-enable only the specific trigger needed for the recovery test.
3. Keep `dry_run: true` until the dispatch path is verified.
4. Re-enable real Threads reply only after a fresh manual decision.
5. Update this file with the recovery date and exact trigger restored.

