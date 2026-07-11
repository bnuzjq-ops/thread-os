import crypto from "node:crypto";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
    },
  });
}

function textResponse(body, status = 200) {
  return new Response(body, {
    status,
    headers: {
      "content-type": "text/plain; charset=utf-8",
    },
  });
}

function normalizePathname(pathname) {
  if (!pathname || pathname === "/") {
    return "/";
  }
  return pathname.replace(/\/+$/, "") || "/";
}

function readHeader(headers, name) {
  return headers.get(name) ?? headers.get(name.toLowerCase()) ?? "";
}

function nowIso() {
  return new Date().toISOString();
}

function uuid() {
  return crypto.randomUUID();
}

function taskIdFor(commentId) {
  return `reply:${commentId}`;
}

function requireStateToken(request, env) {
  const expected = String(env.STATE_API_TOKEN ?? "").trim();
  if (!expected) {
    return { ok: false, status: 500, error: "Missing STATE_API_TOKEN" };
  }

  const header = readHeader(request.headers, "authorization");
  const token = header.startsWith("Bearer ") ? header.slice(7).trim() : "";
  if (!token) {
    return { ok: false, status: 401, error: "Missing state API token" };
  }

  if (token !== expected) {
    return { ok: false, status: 401, error: "Invalid state API token" };
  }

  return { ok: true };
}

async function readJsonBody(request) {
  const text = await request.text();
  if (!text.trim()) {
    return {};
  }

  try {
    return JSON.parse(text);
  } catch {
    throw new Error("invalid json");
  }
}

function toBool(value) {
  return Boolean(value);
}

function toTask(row) {
  if (!row) {
    return null;
  }

  return {
    reply_task_id: String(row.task_id),
    comment_id: String(row.comment_id),
    media_id: String(row.media_id ?? ""),
    status: String(row.status),
    draft: String(row.draft ?? ""),
    draft_version: Number(row.draft_version ?? 0),
    draft_source: String(row.draft_source ?? ""),
    feishu_message_id: row.feishu_message_id ? String(row.feishu_message_id) : null,
    reply_id: row.reply_id ? String(row.reply_id) : null,
    claimed_at: row.claimed_at ? String(row.claimed_at) : null,
    lease_until: row.lease_until ? String(row.lease_until) : null,
    claimed_by: row.claimed_by ? String(row.claimed_by) : null,
    last_error: row.last_error ? String(row.last_error) : null,
    requires_manual_check: toBool(row.requires_manual_check),
    created_at: row.created_at ? String(row.created_at) : null,
    updated_at: row.updated_at ? String(row.updated_at) : null,
  };
}

class StateTaskRepository {
  constructor(db, deps = {}) {
    this.db = db;
    this.now = deps.now ?? nowIso;
    this.uuid = deps.uuid ?? uuid;
  }

  async createTask(commentId, mediaId = "") {
    const existing = await this.getTaskByCommentId(commentId);
    if (existing) {
      return {
        ok: true,
        created: false,
        already_exists: true,
        task: existing,
      };
    }

    const timestamp = this.now();
    const task = {
      reply_task_id: taskIdFor(commentId),
      comment_id: commentId,
      media_id: mediaId,
      status: "detected",
      draft: "",
      draft_version: 0,
      draft_source: "",
      feishu_message_id: null,
      reply_id: null,
      claimed_at: null,
      lease_until: null,
      claimed_by: null,
      last_error: null,
      requires_manual_check: false,
      created_at: timestamp,
      updated_at: timestamp,
    };

    await this.db
      .prepare(
        `INSERT INTO reply_tasks (
          task_id, comment_id, media_id, status,
          draft, draft_version, draft_source,
          feishu_message_id, reply_id,
          claimed_at, lease_until, claimed_by,
          last_error, requires_manual_check,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        task.reply_task_id,
        task.comment_id,
        task.media_id,
        task.status,
        task.draft,
        task.draft_version,
        task.draft_source,
        task.feishu_message_id,
        task.reply_id,
        task.claimed_at,
        task.lease_until,
        task.claimed_by,
        task.last_error,
        task.requires_manual_check ? 1 : 0,
        task.created_at,
        task.updated_at,
      )
      .run();

    await this._recordEvent(task.reply_task_id, "create_task", null, task.status, {
      comment_id: commentId,
      media_id: mediaId,
    });

    return {
      ok: true,
      created: true,
      already_exists: false,
      task,
    };
  }

  async getTask(taskId) {
    return this._selectTask("task_id = ?", [taskId]);
  }

  async getTaskByCommentId(commentId) {
    return this._selectTask("comment_id = ?", [commentId]);
  }

  async saveDraft(taskId, draft, draftSource = "") {
    const task = await this._requireTask(taskId);
    const updatedAt = this.now();
    const nextVersion = Number(task.draft_version ?? 0) + 1;

    await this.db
      .prepare(
        `UPDATE reply_tasks
         SET draft = ?,
             draft_version = ?,
             draft_source = ?,
             status = 'drafted',
             last_error = NULL,
             updated_at = ?
         WHERE task_id = ?`,
      )
      .bind(draft, nextVersion, draftSource, updatedAt, taskId)
      .run();

    await this._recordEvent(taskId, "save_draft", task.status, "drafted", {
      draft_version: nextVersion,
    });

    return this._selectTask("task_id = ?", [taskId]);
  }

  async saveFeishuMessage(taskId, feishuMessageId) {
    const task = await this._requireTask(taskId);
    const updatedAt = this.now();

    await this.db
      .prepare(
        `UPDATE reply_tasks
         SET feishu_message_id = ?,
             status = 'awaiting_review',
             last_error = NULL,
             updated_at = ?
         WHERE task_id = ?`,
      )
      .bind(feishuMessageId, updatedAt, taskId)
      .run();

    await this._recordEvent(taskId, "save_feishu_message", task.status, "awaiting_review", {
      feishu_message_id: feishuMessageId,
    });

    return this._selectTask("task_id = ?", [taskId]);
  }

  async claimSend(taskId, draftVersion, claimedBy = "") {
    const task = await this._requireTask(taskId);
    const leaseUntil = this._leaseUntilIso(15 * 60 * 1000);
    const updatedAt = this.now();

    const result = await this.db
      .prepare(
        `UPDATE reply_tasks
         SET status = 'sending',
             claimed_at = ?,
             lease_until = ?,
             claimed_by = ?,
             updated_at = ?
         WHERE task_id = ?
           AND comment_id = ?
           AND status = 'awaiting_review'
           AND draft_version = ?`,
      )
      .bind(updatedAt, leaseUntil, claimedBy, updatedAt, taskId, task.comment_id, draftVersion)
      .run();

    const changes = result?.meta?.changes ?? 0;
    if (changes === 1) {
      const claimed = await this._selectTask("task_id = ?", [taskId]);
      await this._recordEvent(taskId, "claim_send", task.status, "sending", {
        claimed_by: claimedBy,
      });
      return {
        ok: true,
        claimed: true,
        reason: null,
        task: claimed,
      };
    }

    return {
      ok: false,
      claimed: false,
      reason: "already_claimed_or_stale_version",
      task,
    };
  }

  async completeSend(taskId, replyId) {
    const task = await this._requireTask(taskId);
    const updatedAt = this.now();
    await this.db
      .prepare(
        `UPDATE reply_tasks
         SET status = 'sent',
             reply_id = ?,
             last_error = NULL,
             updated_at = ?
         WHERE task_id = ?
           AND status = 'sending'`,
      )
      .bind(replyId, updatedAt, taskId)
      .run();

    const updated = await this._selectTask("task_id = ?", [taskId]);
    await this._recordEvent(taskId, "complete_send", task.status, "sent", {
      reply_id: replyId,
    });
    return updated;
  }

  async failTask(taskId, error) {
    const task = await this._requireTask(taskId);
    const updatedAt = this.now();
    await this.db
      .prepare(
        `UPDATE reply_tasks
         SET status = 'failed',
             last_error = ?,
             updated_at = ?
         WHERE task_id = ?`,
      )
      .bind(error, updatedAt, taskId)
      .run();

    await this._recordEvent(taskId, "fail_task", task.status, "failed", {
      error,
    });
    return this._selectTask("task_id = ?", [taskId]);
  }

  async markUnknown(taskId, error) {
    const task = await this._requireTask(taskId);
    const updatedAt = this.now();
    await this.db
      .prepare(
        `UPDATE reply_tasks
         SET status = 'unknown',
             last_error = ?,
             updated_at = ?
         WHERE task_id = ?`,
      )
      .bind(error, updatedAt, taskId)
      .run();

    await this._recordEvent(taskId, "mark_unknown", task.status, "unknown", {
      error,
    });
    return this._selectTask("task_id = ?", [taskId]);
  }

  async _selectTask(whereClause, binds) {
    const row = await this.db
      .prepare(
        `SELECT
           task_id,
           comment_id,
           media_id,
           status,
           draft,
           draft_version,
           draft_source,
           feishu_message_id,
           reply_id,
           claimed_at,
           lease_until,
           claimed_by,
           last_error,
           requires_manual_check,
           created_at,
           updated_at
         FROM reply_tasks
         WHERE ${whereClause}
         LIMIT 1`,
      )
      .bind(...binds)
      .first();

    return toTask(row);
  }

  async _requireTask(taskId) {
    const task = await this._selectTask("task_id = ?", [taskId]);
    if (!task) {
      throw new Error(`Reply task not found: ${taskId}`);
    }
    return task;
  }

  async _recordEvent(taskId, eventType, fromStatus, toStatus, detail) {
    await this.db
      .prepare(
        `INSERT INTO task_events (
           event_id, task_id, event_type, from_status, to_status, detail, created_at
         ) VALUES (?, ?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        this.uuid(),
        taskId,
        eventType,
        fromStatus,
        toStatus,
        detail ? JSON.stringify(detail) : null,
        this.now(),
      )
      .run();
  }

  _leaseUntilIso(durationMs) {
    return new Date(Date.now() + durationMs).toISOString();
  }
}

export { StateTaskRepository };

async function handleCreateTask(repo, request) {
  const body = await readJsonBody(request);
  const commentId = String(body.comment_id ?? "").trim();
  const mediaId = String(body.media_id ?? "").trim();
  if (!commentId) {
    return jsonResponse({ ok: false, error: "Missing comment_id" }, 400);
  }

  const result = await repo.createTask(commentId, mediaId);
  return jsonResponse(result);
}

async function handleGetTask(repo, taskId) {
  const task = await repo.getTask(taskId);
  if (!task) {
    return jsonResponse({ ok: false, error: "not found" }, 404);
  }
  return jsonResponse({ ok: true, task });
}

async function handleSaveDraft(repo, request, taskId) {
  const body = await readJsonBody(request);
  const draft = String(body.draft ?? "").trim();
  if (!draft) {
    return jsonResponse({ ok: false, error: "Missing draft" }, 400);
  }
  const task = await repo.saveDraft(taskId, draft, String(body.draft_source ?? "").trim());
  return jsonResponse({ ok: true, task });
}

async function handleSaveFeishuMessage(repo, request, taskId) {
  const body = await readJsonBody(request);
  const messageId = String(body.feishu_message_id ?? "").trim();
  if (!messageId) {
    return jsonResponse({ ok: false, error: "Missing feishu_message_id" }, 400);
  }
  const task = await repo.saveFeishuMessage(taskId, messageId);
  return jsonResponse({ ok: true, task });
}

async function handleClaimSend(repo, request, taskId) {
  const body = await readJsonBody(request);
  const draftVersion = Number(body.draft_version);
  if (!Number.isFinite(draftVersion)) {
    return jsonResponse({ ok: false, claimed: false, reason: "Missing draft_version" }, 400);
  }
  const result = await repo.claimSend(taskId, draftVersion, String(body.claimed_by ?? "").trim());
  return jsonResponse(result);
}

async function handleCompleteSend(repo, request, taskId) {
  const body = await readJsonBody(request);
  const replyId = String(body.reply_id ?? "").trim();
  if (!replyId) {
    return jsonResponse({ ok: false, error: "Missing reply_id" }, 400);
  }
  const task = await repo.completeSend(taskId, replyId);
  return jsonResponse({ ok: true, task });
}

async function handleFailTask(repo, request, taskId) {
  const body = await readJsonBody(request);
  const error = String(body.error ?? "").trim();
  if (!error) {
    return jsonResponse({ ok: false, error: "Missing error" }, 400);
  }
  const task = await repo.failTask(taskId, error);
  return jsonResponse({ ok: true, task });
}

async function handleMarkUnknown(repo, request, taskId) {
  const body = await readJsonBody(request);
  const error = String(body.error ?? "").trim();
  if (!error) {
    return jsonResponse({ ok: false, error: "Missing error" }, 400);
  }
  const task = await repo.markUnknown(taskId, error);
  return jsonResponse({ ok: true, task });
}

export async function handleStateRequest(request, env = {}, deps = {}) {
  const url = new URL(request.url);
  const pathname = normalizePathname(url.pathname);

  if (pathname === "/health") {
    return textResponse("ok");
  }

  const auth = requireStateToken(request, env);
  if (!auth.ok) {
    return jsonResponse({ error: auth.error }, auth.status);
  }

  const db = env.DB;
  if (!db) {
    return jsonResponse({ error: "Missing DB binding" }, 500);
  }

  const repo = deps.repository ?? new StateTaskRepository(db, deps);

  if (pathname === "/v1/reply-tasks" && request.method === "POST") {
    try {
      return await handleCreateTask(repo, request);
    } catch (error) {
      return jsonResponse({ ok: false, error: String(error instanceof Error ? error.message : error) }, 500);
    }
  }

  const match = pathname.match(/^\/v1\/reply-tasks\/([^/]+)(?:\/([^/]+))?$/);
  if (!match) {
    return jsonResponse({ error: "not found" }, 404);
  }

  const taskId = decodeURIComponent(match[1]);
  const action = match[2] ?? null;

  try {
    if (request.method === "GET" && !action) {
      return await handleGetTask(repo, taskId);
    }
    if (request.method === "POST" && action === "draft") {
      return await handleSaveDraft(repo, request, taskId);
    }
    if (request.method === "POST" && action === "feishu-message") {
      return await handleSaveFeishuMessage(repo, request, taskId);
    }
    if (request.method === "POST" && action === "claim-send") {
      return await handleClaimSend(repo, request, taskId);
    }
    if (request.method === "POST" && action === "complete") {
      return await handleCompleteSend(repo, request, taskId);
    }
    if (request.method === "POST" && action === "fail") {
      return await handleFailTask(repo, request, taskId);
    }
    if (request.method === "POST" && action === "unknown") {
      return await handleMarkUnknown(repo, request, taskId);
    }
  } catch (error) {
    return jsonResponse({ ok: false, error: String(error instanceof Error ? error.message : error) }, 500);
  }

  return jsonResponse({ error: "method not allowed" }, 405);
}

export default {
  fetch(request, env, ctx) {
    return handleStateRequest(request, env, { ctx });
  },
};
