# JSON Business Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the publish and human-reviewed reply workflows locally using JSON state, without real external calls or D1 integration.

**Architecture:** JSON remains the only runtime store. A Markdown fixture creates a publish task, then a fake Threads client verifies each terminal state. Reply monitoring and dispatch continue through `TaskStore`; explicit API failures are recorded as `failed`, delivery-uncertain failures as `unknown`, and duplicate claims never call Threads twice. GitHub workflow state commits are documented as an MVP bridge only.

**Tech Stack:** Python standard library, unittest, JSON files, GitHub Actions YAML.

---

### Task 1: Freeze the publish contract

**Files:**
- Create: `tests/fixtures/posts/test-post.md`
- Modify: `tests/test_publish_store.py`
- Modify: `threads_bot_system/publish_task.py`
- Modify: `threads_bot_system/publish_state.py`

- [ ] Add a failing test that creates a task from `content_id`, expects `ready`, and verifies that legacy `pending` records load as `ready`.
- [ ] Run `python -m unittest tests.test_publish_store` and confirm the status assertion fails.
- [ ] Make the smallest enum/parser change: canonical pending state is `ready`; accept old `pending` JSON on load.
- [ ] Run `python -m unittest tests.test_publish_store` and confirm it passes.

### Task 2: Make the publish input and terminal states testable

**Files:**
- Create: `threads_bot_system/publish_source.py`
- Modify: `threads_bot_system/cli.py`
- Modify: `threads_bot_system/publish_task.py`
- Modify: `threads_bot_system/publish_state.py`
- Modify: `threads_bot_system/publish_store.py`
- Modify: `threads_bot_system/publish_runtime.py`
- Modify: `tests/test_publish_runtime.py`
- Modify: `tests/test_cli.py`

- [ ] Add failing tests for `--source tests/fixtures/posts/test-post.md`, empty body -> `failed`, timeout -> `unknown`, duplicate `content_id` -> one API call, and successful `post_id` persistence.
- [ ] Run `python -m unittest tests.test_publish_runtime tests.test_cli` and confirm the new assertions fail.
- [ ] Parse only the required frontmatter fields (`content_id`, `platform`, `status`) and body; create/reuse one JSON task; classify `TimeoutError` as unknown and explicit API errors as failed.
- [ ] Run the same tests and confirm they pass.

### Task 3: Make reply errors explicit and idempotent

**Files:**
- Modify: `threads_bot_system/reply_runtime.py`
- Modify: `tests/test_reply_runtime.py`

- [ ] Add failing tests for DeepSeek failure -> failed/no review card, Threads timeout -> unknown/no retry, stale draft version -> no publish call, and repeated send -> one publish call.
- [ ] Run `python -m unittest tests.test_reply_runtime` and confirm each new assertion fails.
- [ ] Keep deterministic local drafting only when no DeepSeek client was supplied; when a supplied client fails, persist `failed` and do not send a card. Classify delivery-uncertain Threads exceptions as `unknown`.
- [ ] Run `python -m unittest tests.test_reply_runtime` and confirm it passes.

### Task 4: Persist and report reply dispatch state in the MVP workflow

**Files:**
- Modify: `.github/workflows/reply-monitor.yml`
- Modify: `.github/workflows/reply-dispatch.yml`
- Modify: `threads_bot_system/feishu_api.py`
- Modify: `threads_bot_system/reply_runtime.py`
- Modify: `tests/test_feishu_api.py`
- Modify: `tests/test_reply_runtime.py`

- [ ] Add failing tests for a successful dispatch calling an injected final-result notifier after `reply_id` exists; notification failure must not turn a sent reply into an unsent reply.
- [ ] Run the focused tests and confirm the notifier behavior fails.
- [ ] Add a small text-status notification method, inject it optionally into dispatch, configure both reply workflows with one shared concurrency group, and commit the JSON state in dispatch using `contents: write`.
- [ ] Run the focused tests and confirm they pass.

### Task 5: Document current truth and the future content contract

**Files:**
- Modify: `ARCHITECTURE.md`
- Modify: `CONTEXT.md`
- Modify: `README.md`
- Modify: `RUNBOOK.md`
- Modify: `SPEC.md`
- Modify: `RESTART_HANDOFF.md`

- [ ] Document JSON as the MVP integration backend, D1 as deferred, separate State/Feishu Workers, no real integration completed, and workflow commits as temporary state persistence.
- [ ] Add the Obsidian source contract only: `pending/`, frontmatter fields, body rules, one-item selection, no image support in MVP, and read-only GitHub acquisition to be decided before remote integration.
- [ ] Run `python -m unittest discover -s tests` and verify no doc claim exceeds the tested behavior.

### Task 6: Final verification

**Files:**
- Test: `tests/`

- [ ] Run `python -m unittest discover -s tests`.
- [ ] Run `node --test tests/reply_worker.test.mjs` if Node is available.
- [ ] Confirm no external API, D1, Worker deployment, Obsidian repository, secret, cron, or push action was invoked.
