# Acceptance Checklist

Allowed statuses: `PASS`, `FAIL`, `BLOCKED`, `NOT_TESTED`.

## Current Summary

| Area | Status | Evidence or blocker |
| --- | --- | --- |
| Content export and queue contract | PASS | Export tool and queue Workflow tests |
| Scheduled time and UTC selection | PASS | Source/runtime tests and scheduled selector |
| Threads two-step publish | PASS | Real post permalink in `docs/ACCEPTANCE_STATUS.md` |
| Publish state, idempotency, and recovery metadata | PASS | Python tests and JSON state contract |
| Corrupt JSON fail-closed | PASS | `tests/test_publish_store.py` |
| Repository Secret scan | PASS | Current tracked files and Git history pattern scan found no configured keys |
| Workflow concurrency and recovery artifacts | PASS | `tests/test_workflow_contract.py` |
| DeepSeek independent API call | PASS | GitHub run `29197690303` |
| Reply code-level state machine | PASS | Python reply/task-store tests |
| Worker signature and payload contract | PASS | `tests/reply_worker.test.mjs` |
| Safe reply dry-run code | PASS | `tests/test_reply_runtime.py` |
| Live Feishu/dispatch dry-run | NOT_TESTED | Requires real Feishu test receipt |
| Continuous three-post publish acceptance | NOT_TESTED | Requires real external publishing |
| Real comment reply end to end | BLOCKED | `no_new_real_comment`; unblock with a new unprocessed comment |

## Rules

- No item may be `PASS` without evidence.
- `BLOCKED` does not mean `FAIL` and does not pause unrelated development.
- A real publish or reply must never be repeated solely because state writeback or permalink lookup failed.
- Mock and dry-run evidence must not be described as real platform success.
