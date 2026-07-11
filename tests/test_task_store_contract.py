import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlparse

from threads_bot_system.reply_state import task_to_record
from threads_bot_system.reply_task import ReplyTaskStatus, new_reply_task
from threads_bot_system.state_api_task_store import StateApiTaskStore
from threads_bot_system.task_store import JsonTaskStore


class DummyResponse:
    def __init__(self, body: str, status: int = 200) -> None:
        self._body = body.encode("utf-8")
        self.status = status

    def read(self) -> bytes:
        return self._body


class FakeStateApiService:
    def __init__(self) -> None:
        self.tasks: dict[str, dict[str, object]] = {}
        self.fail_paths: set[str] = set()

    def seed_task(self, task: dict[str, object]) -> None:
        self.tasks[str(task["reply_task_id"])] = dict(task)

    def request(self, request: object) -> DummyResponse:
        path = urlparse(request.full_url).path
        if path in self.fail_paths:
            raise OSError(f"State API unavailable: {path}")

        method = request.get_method()
        body = json.loads(request.data.decode("utf-8")) if getattr(request, "data", None) else {}
        parts = path.strip("/").split("/")

        if method == "POST" and parts == ["v1", "reply-tasks"]:
            return self._create_task(body)

        if len(parts) >= 3 and parts[:2] == ["v1", "reply-tasks"]:
            task_id = parts[2]
            action = parts[3] if len(parts) == 4 else None
            if method == "GET" and action is None:
                task = self.tasks.get(task_id)
                if task is None:
                    return self._json({"ok": False, "error": "not found"}, 404)
                return self._json({"ok": True, "task": task})
            if method == "POST" and action == "draft":
                return self._save_draft(task_id, body)
            if method == "POST" and action == "feishu-message":
                return self._save_feishu_message(task_id, body)
            if method == "POST" and action == "claim-send":
                return self._claim_send(task_id, body)
            if method == "POST" and action == "complete":
                return self._complete_send(task_id, body)
            if method == "POST" and action == "fail":
                return self._fail_task(task_id, body)
            if method == "POST" and action == "unknown":
                return self._mark_unknown(task_id, body)

        return self._json({"ok": False, "error": "not found"}, 404)

    def _create_task(self, body: dict[str, object]) -> DummyResponse:
        comment_id = str(body.get("comment_id", "")).strip()
        media_id = str(body.get("media_id", "")).strip()
        for task in self.tasks.values():
            if task["comment_id"] == comment_id:
                return self._json(
                    {
                        "ok": True,
                        "created": False,
                        "already_exists": True,
                        "task": task,
                    }
                )

        task_id = f"reply:{comment_id}"
        timestamp = "2026-07-10T00:00:00Z"
        task = {
            "reply_task_id": task_id,
            "comment_id": comment_id,
            "media_id": media_id,
            "status": "detected",
            "draft": "",
            "draft_version": 0,
            "draft_source": "",
            "feishu_message_id": None,
            "reply_id": None,
            "claimed_at": None,
            "lease_until": None,
            "claimed_by": None,
            "last_error": None,
            "requires_manual_check": False,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        self.tasks[task_id] = task
        return self._json(
            {
                "ok": True,
                "created": True,
                "already_exists": False,
                "task": task,
            }
        )

    def _save_draft(self, task_id: str, body: dict[str, object]) -> DummyResponse:
        task = self.tasks[task_id]
        updated = dict(task)
        updated["draft"] = str(body.get("draft", ""))
        updated["draft_version"] = int(updated.get("draft_version", 0)) + 1
        updated["draft_source"] = str(body.get("draft_source", ""))
        updated["status"] = "drafted"
        updated["last_error"] = None
        updated["updated_at"] = "2026-07-10T00:01:00Z"
        self.tasks[task_id] = updated
        return self._json({"ok": True, "task": updated})

    def _save_feishu_message(self, task_id: str, body: dict[str, object]) -> DummyResponse:
        task = self.tasks[task_id]
        updated = dict(task)
        updated["feishu_message_id"] = str(body.get("feishu_message_id", ""))
        updated["status"] = "awaiting_review"
        updated["last_error"] = None
        updated["updated_at"] = "2026-07-10T00:02:00Z"
        self.tasks[task_id] = updated
        return self._json({"ok": True, "task": updated})

    def _claim_send(self, task_id: str, body: dict[str, object]) -> DummyResponse:
        task = self.tasks[task_id]
        draft_version = int(body.get("draft_version", 0))
        if task["status"] != "awaiting_review" or int(task.get("draft_version", 0)) != draft_version:
            return self._json(
                {
                    "ok": False,
                    "claimed": False,
                    "reason": "already_claimed_or_stale_version",
                    "task": task,
                }
            )

        updated = dict(task)
        updated["status"] = "sending"
        updated["claimed_at"] = "2026-07-10T00:03:00Z"
        updated["lease_until"] = "2026-07-10T00:18:00Z"
        updated["claimed_by"] = str(body.get("claimed_by", ""))
        updated["updated_at"] = "2026-07-10T00:03:00Z"
        self.tasks[task_id] = updated
        return self._json({"ok": True, "claimed": True, "reason": None, "task": updated})

    def _complete_send(self, task_id: str, body: dict[str, object]) -> DummyResponse:
        task = self.tasks[task_id]
        updated = dict(task)
        updated["status"] = "sent"
        updated["reply_id"] = str(body.get("reply_id", ""))
        updated["last_error"] = None
        updated["updated_at"] = "2026-07-10T00:04:00Z"
        self.tasks[task_id] = updated
        return self._json({"ok": True, "task": updated})

    def _fail_task(self, task_id: str, body: dict[str, object]) -> DummyResponse:
        task = self.tasks[task_id]
        updated = dict(task)
        updated["status"] = "failed"
        updated["last_error"] = str(body.get("error", ""))
        updated["updated_at"] = "2026-07-10T00:05:00Z"
        self.tasks[task_id] = updated
        return self._json({"ok": True, "task": updated})

    def _mark_unknown(self, task_id: str, body: dict[str, object]) -> DummyResponse:
        task = self.tasks[task_id]
        updated = dict(task)
        updated["status"] = "unknown"
        updated["last_error"] = str(body.get("error", ""))
        updated["updated_at"] = "2026-07-10T00:06:00Z"
        self.tasks[task_id] = updated
        return self._json({"ok": True, "task": updated})

    @staticmethod
    def _json(payload: dict[str, object], status: int = 200) -> DummyResponse:
        return DummyResponse(json.dumps(payload, ensure_ascii=False), status)


def make_seed_task(
    comment_id: str,
    status: ReplyTaskStatus,
    *,
    draft_version: int = 1,
    draft: str = "draft text",
    feishu_message_id: str | None = "msg-1",
    reply_id: str | None = None,
    last_error: str | None = None,
):
    task = new_reply_task(comment_id)
    return replace(
        task,
        status=status,
        draft=draft,
        draft_version=draft_version,
        feishu_message_id=feishu_message_id,
        reply_id=reply_id,
        last_error=last_error,
    )


class TaskStoreContractTests(unittest.TestCase):
    def test_json_task_store_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = JsonTaskStore.load(Path(tmpdir) / "reply_tasks.json")
            self._exercise_contract(
                store,
                lambda comment_id, status, **kwargs: self._seed_json_task(store, comment_id, status, **kwargs),
            )

    def test_state_api_task_store_contract(self) -> None:
        service = FakeStateApiService()
        store = StateApiTaskStore(
            base_url="https://state.example",
            api_token="state-token",
            request_impl=service.request,
        )
        self._exercise_contract(store, lambda comment_id, status, **kwargs: self._seed_state_task(service, comment_id, status, **kwargs))

    def _exercise_contract(self, store, seed_task) -> None:
        self.assertIsNone(store.get_task("reply:missing"))

        first = store.create_task("comment-1", "media-1")
        self.assertTrue(first.ok)
        self.assertTrue(first.created)
        self.assertFalse(first.already_exists)
        self.assertEqual(first.task.reply_task_id, "reply:comment-1")
        self.assertEqual(first.task.media_id, "media-1")

        duplicate = store.create_task("comment-1", "media-1")
        self.assertTrue(duplicate.ok)
        self.assertFalse(duplicate.created)
        self.assertTrue(duplicate.already_exists)
        self.assertEqual(duplicate.task.reply_task_id, first.task.reply_task_id)

        drafted = store.save_draft(first.task.reply_task_id, "draft text")
        self.assertEqual(drafted.status, ReplyTaskStatus.DRAFTED)
        self.assertEqual(drafted.draft_version, 1)
        self.assertEqual(drafted.draft, "draft text")

        reviewed = store.save_feishu_message(first.task.reply_task_id, "msg-1")
        self.assertEqual(reviewed.status, ReplyTaskStatus.AWAITING_REVIEW)
        self.assertEqual(reviewed.feishu_message_id, "msg-1")

        claimed = store.claim_send(first.task.reply_task_id, reviewed.draft_version)
        self.assertTrue(claimed.ok)
        self.assertTrue(claimed.claimed)
        self.assertIsNotNone(claimed.task)
        self.assertEqual(claimed.task.status, ReplyTaskStatus.SENDING)

        second_claim = store.claim_send(first.task.reply_task_id, reviewed.draft_version)
        self.assertFalse(second_claim.ok)
        self.assertFalse(second_claim.claimed)
        self.assertEqual(second_claim.reason, "already_claimed_or_stale_version")
        self.assertEqual(second_claim.task.status, ReplyTaskStatus.SENDING)

        sent = store.complete_send(first.task.reply_task_id, "reply-1")
        self.assertEqual(sent.status, ReplyTaskStatus.SENT)
        self.assertEqual(sent.reply_id, "reply-1")

        sent_claim = store.claim_send(first.task.reply_task_id, reviewed.draft_version)
        self.assertFalse(sent_claim.claimed)
        self.assertEqual(sent_claim.task.status, ReplyTaskStatus.SENT)

        stale = store.create_task("comment-2", "media-1")
        stale_drafted = store.save_draft(stale.task.reply_task_id, "draft text 2")
        store.save_feishu_message(stale.task.reply_task_id, "msg-2")
        stale_claim = store.claim_send(stale.task.reply_task_id, stale_drafted.draft_version - 1)
        self.assertFalse(stale_claim.claimed)
        self.assertEqual(stale_claim.reason, "already_claimed_or_stale_version")

        skipped = seed_task("comment-3", ReplyTaskStatus.SKIPPED, draft_version=1)
        skipped_claim = store.claim_send(skipped.reply_task_id, skipped.draft_version)
        self.assertFalse(skipped_claim.claimed)
        self.assertEqual(skipped_claim.task.status, ReplyTaskStatus.SKIPPED)

        sending = seed_task("comment-4", ReplyTaskStatus.SENDING, draft_version=1)
        sending_claim = store.claim_send(sending.reply_task_id, sending.draft_version)
        self.assertFalse(sending_claim.claimed)
        self.assertEqual(sending_claim.task.status, ReplyTaskStatus.SENDING)

        failed = store.fail_task(first.task.reply_task_id, "boom")
        self.assertEqual(failed.status, ReplyTaskStatus.FAILED)
        self.assertEqual(failed.last_error, "boom")

        unknown = store.mark_unknown(first.task.reply_task_id, "mystery")
        self.assertEqual(unknown.status, ReplyTaskStatus.UNKNOWN)
        self.assertEqual(unknown.last_error, "mystery")

    def _seed_json_task(
        self,
        store: JsonTaskStore,
        comment_id: str,
        status: ReplyTaskStatus,
        *,
        draft_version: int = 1,
        draft: str = "draft text",
        feishu_message_id: str | None = "msg-1",
        reply_id: str | None = None,
        last_error: str | None = None,
    ):
        task = make_seed_task(
            comment_id,
            status,
            draft_version=draft_version,
            draft=draft,
            feishu_message_id=feishu_message_id,
            reply_id=reply_id,
            last_error=last_error,
        )
        store.upsert(task)
        store.save()
        return store.get(task.reply_task_id)

    def _seed_state_task(
        self,
        service: FakeStateApiService,
        comment_id: str,
        status: ReplyTaskStatus,
        *,
        draft_version: int = 1,
        draft: str = "draft text",
        feishu_message_id: str | None = "msg-1",
        reply_id: str | None = None,
        last_error: str | None = None,
    ):
        task = make_seed_task(
            comment_id,
            status,
            draft_version=draft_version,
            draft=draft,
            feishu_message_id=feishu_message_id,
            reply_id=reply_id,
            last_error=last_error,
        )
        service.seed_task(task_to_record(task))
        return task


if __name__ == "__main__":
    unittest.main()
