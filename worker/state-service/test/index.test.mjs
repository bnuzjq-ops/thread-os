import assert from "node:assert/strict";
import test from "node:test";

import { StateTaskRepository, handleStateRequest } from "../src/index.mjs";

class FakeResult {
  constructor(changes) {
    this.meta = { changes };
  }
}

class FakeStatement {
  constructor(db, sql) {
    this.db = db;
    this.sql = sql;
    this.bindings = [];
  }

  bind(...bindings) {
    this.bindings = bindings;
    return this;
  }

  async run() {
    return this.db.run(this.sql, this.bindings);
  }

  async first() {
    return this.db.first(this.sql, this.bindings);
  }
}

class FakeD1Database {
  constructor() {
    this.tasks = new Map();
    this.events = [];
    this.eventCounter = 0;
  }

  prepare(sql) {
    return new FakeStatement(this, sql);
  }

  async run(sql, bindings) {
    if (sql.includes("INSERT INTO reply_tasks")) {
      const task = {
        task_id: bindings[0],
        comment_id: bindings[1],
        media_id: bindings[2],
        status: bindings[3],
        draft: bindings[4],
        draft_version: bindings[5],
        draft_source: bindings[6],
        feishu_message_id: bindings[7],
        reply_id: bindings[8],
        claimed_at: bindings[9],
        lease_until: bindings[10],
        claimed_by: bindings[11],
        last_error: bindings[12],
        requires_manual_check: bindings[13],
        created_at: bindings[14],
        updated_at: bindings[15],
      };
      this.tasks.set(task.task_id, task);
      return new FakeResult(1);
    }

    if (sql.includes("SET draft = ?")) {
      const [draft, nextVersion, draftSource, updatedAt, taskId] = bindings;
      const task = this.tasks.get(taskId);
      if (!task) {
        return new FakeResult(0);
      }
      Object.assign(task, {
        draft,
        draft_version: nextVersion,
        draft_source: draftSource,
        status: "drafted",
        last_error: null,
        updated_at: updatedAt,
      });
      return new FakeResult(1);
    }

    if (sql.includes("SET feishu_message_id = ?")) {
      const [feishuMessageId, updatedAt, taskId] = bindings;
      const task = this.tasks.get(taskId);
      if (!task) {
        return new FakeResult(0);
      }
      Object.assign(task, {
        feishu_message_id: feishuMessageId,
        status: "awaiting_review",
        last_error: null,
        updated_at: updatedAt,
      });
      return new FakeResult(1);
    }

    if (sql.includes("SET status = 'sending'")) {
      const [updatedAt, leaseUntil, claimedBy, claimedUpdatedAt, taskId, commentId, draftVersion] = bindings;
      const task = this.tasks.get(taskId);
      if (
        !task ||
        task.comment_id !== commentId ||
        task.status !== "awaiting_review" ||
        Number(task.draft_version) !== Number(draftVersion)
      ) {
        return new FakeResult(0);
      }
      Object.assign(task, {
        status: "sending",
        claimed_at: updatedAt,
        lease_until: leaseUntil,
        claimed_by: claimedBy,
        updated_at: claimedUpdatedAt,
      });
      return new FakeResult(1);
    }

    if (sql.includes("SET status = 'sent'")) {
      const [replyId, updatedAt, taskId] = bindings;
      const task = this.tasks.get(taskId);
      if (!task || task.status !== "sending") {
        return new FakeResult(0);
      }
      Object.assign(task, {
        status: "sent",
        reply_id: replyId,
        last_error: null,
        updated_at: updatedAt,
      });
      return new FakeResult(1);
    }

    if (sql.includes("SET status = 'failed'")) {
      const [error, updatedAt, taskId] = bindings;
      const task = this.tasks.get(taskId);
      if (!task) {
        return new FakeResult(0);
      }
      Object.assign(task, {
        status: "failed",
        last_error: error,
        updated_at: updatedAt,
      });
      return new FakeResult(1);
    }

    if (sql.includes("SET status = 'unknown'")) {
      const [error, updatedAt, taskId] = bindings;
      const task = this.tasks.get(taskId);
      if (!task) {
        return new FakeResult(0);
      }
      Object.assign(task, {
        status: "unknown",
        last_error: error,
        updated_at: updatedAt,
      });
      return new FakeResult(1);
    }

    if (sql.includes("INSERT INTO task_events")) {
      const [eventId, taskId, eventType, fromStatus, toStatus, detail, createdAt] = bindings;
      this.events.push({
        event_id: eventId,
        task_id: taskId,
        event_type: eventType,
        from_status: fromStatus,
        to_status: toStatus,
        detail,
        created_at: createdAt,
      });
      return new FakeResult(1);
    }

    return new FakeResult(0);
  }

  async first(sql, bindings) {
    if (sql.includes("WHERE task_id = ?")) {
      return this._clone(this.tasks.get(bindings[0]));
    }
    if (sql.includes("WHERE comment_id = ?")) {
      for (const task of this.tasks.values()) {
        if (task.comment_id === bindings[0]) {
          return this._clone(task);
        }
      }
      return null;
    }
    return null;
  }

  _clone(task) {
    if (!task) {
      return null;
    }
    return { ...task };
  }
}

test("state worker repository keeps claim_send atomic and single-use", async () => {
  const db = new FakeD1Database();
  const repo = new StateTaskRepository(db, {
    now: () => "2026-07-10T12:00:00Z",
    uuid: () => `event-${db.eventCounter += 1}`,
  });

  const created = await repo.createTask("comment-1", "media-1");
  assert.equal(created.created, true);
  assert.equal(created.task.reply_task_id, "reply:comment-1");

  const duplicate = await repo.createTask("comment-1", "media-1");
  assert.equal(duplicate.created, false);
  assert.equal(duplicate.already_exists, true);

  const drafted = await repo.saveDraft("reply:comment-1", "draft text");
  assert.equal(drafted.status, "drafted");
  assert.equal(drafted.draft_version, 1);

  const reviewed = await repo.saveFeishuMessage("reply:comment-1", "msg-1");
  assert.equal(reviewed.status, "awaiting_review");

  const claimed = await repo.claimSend("reply:comment-1", 1);
  assert.equal(claimed.claimed, true);
  assert.equal(claimed.task.status, "sending");

  const secondClaim = await repo.claimSend("reply:comment-1", 1);
  assert.equal(secondClaim.claimed, false);
  assert.equal(secondClaim.reason, "already_claimed_or_stale_version");
  assert.equal(secondClaim.task.status, "sending");

  const sent = await repo.completeSend("reply:comment-1", "reply-1");
  assert.equal(sent.status, "sent");
  assert.equal(sent.reply_id, "reply-1");

  const claimAfterSent = await repo.claimSend("reply:comment-1", 1);
  assert.equal(claimAfterSent.claimed, false);
  assert.equal(claimAfterSent.task.status, "sent");

  const stale = await repo.createTask("comment-2", "media-1");
  await repo.saveDraft(stale.task.reply_task_id, "draft text 2");
  await repo.saveFeishuMessage(stale.task.reply_task_id, "msg-2");
  const staleClaim = await repo.claimSend(stale.task.reply_task_id, 0);
  assert.equal(staleClaim.claimed, false);
  assert.equal(staleClaim.reason, "already_claimed_or_stale_version");

  db.tasks.set("reply:comment-3", {
    task_id: "reply:comment-3",
    comment_id: "comment-3",
    media_id: "media-1",
    status: "skipped",
    draft: "draft",
    draft_version: 1,
    draft_source: "",
    feishu_message_id: "msg-3",
    reply_id: null,
    claimed_at: null,
    lease_until: null,
    claimed_by: null,
    last_error: "skip_requested",
    requires_manual_check: 0,
    created_at: "2026-07-10T12:00:00Z",
    updated_at: "2026-07-10T12:00:00Z",
  });
  const skippedClaim = await repo.claimSend("reply:comment-3", 1);
  assert.equal(skippedClaim.claimed, false);
  assert.equal(skippedClaim.task.status, "skipped");
});

test("state worker routes health and create_task", async () => {
  const repo = {
    async createTask(commentId, mediaId) {
      return {
        ok: true,
        created: true,
        already_exists: false,
        task: {
          reply_task_id: `reply:${commentId}`,
          comment_id: commentId,
          media_id: mediaId,
          status: "detected",
        },
      };
    },
  };

  const health = await handleStateRequest(new Request("https://example.com/health"), {
    STATE_API_TOKEN: "secret",
    DB: {},
  });
  assert.equal(health.status, 200);
  assert.equal(await health.text(), "ok");

  const create = await handleStateRequest(
    new Request("https://example.com/v1/reply-tasks", {
      method: "POST",
      headers: {
        Authorization: "Bearer secret",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        comment_id: "comment-1",
        media_id: "media-1",
      }),
    }),
    {
      STATE_API_TOKEN: "secret",
      DB: {},
    },
    { repository: repo },
  );

  assert.equal(create.status, 200);
  const body = await create.json();
  assert.equal(body.ok, true);
  assert.equal(body.task.reply_task_id, "reply:comment-1");
});
