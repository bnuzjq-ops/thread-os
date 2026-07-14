import { WorkflowEntrypoint } from "cloudflare:workers";

export interface ScheduleParams {
  content_id: string;
  content_version: number;
  scheduled_time: string;
  latest_publish_time: string;
  snapshot_repo: string;
  snapshot_commit: string;
  snapshot_path: string;
  trace_id: string;
}

interface Env {
  PUBLISH_SCHEDULES: Workflow<ScheduleParams>;
  SCHEDULER_API_TOKEN: string;
  GITHUB_PAT: string;
  GITHUB_REPOSITORY: string;
  GITHUB_EVENT_TYPE: string;
}

const MAX_DISPATCH_ATTEMPTS = 3;
const MIN_LEAD_MS = 5 * 60 * 1000;
const DEFAULT_EVENT_TYPE = "threads_publish_scheduled";

export class PublishScheduleWorkflow extends WorkflowEntrypoint<Env, ScheduleParams> {
  async run(event: WorkflowEvent<ScheduleParams>, step: WorkflowStep) {
    const params = validateSchedule(event.payload);
    await step.sleepUntil("wait-until-scheduled", new Date(params.scheduled_time));
    const now = Date.now();
    if (now > Date.parse(params.latest_publish_time)) {
      await step.do("record-missed", async () => {
        await createIssue(this.env, params, "missed", "The publish window expired before dispatch.");
      });
      return { status: "missed", content_id: params.content_id };
    }
    const dispatched = await step.do("dispatch-github", async () => dispatchGitHub(this.env, params));
    if (!dispatched) {
      await step.do("record-dispatch-failure", async () => {
        await createIssue(this.env, params, "scheduler_dispatch_failed", "GitHub repository_dispatch failed after three attempts.");
      });
      return { status: "failed", content_id: params.content_id };
    }
    return { status: "dispatched", content_id: params.content_id, trace_id: params.trace_id };
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") return new Response("ok");
    if (request.method === "POST" && url.pathname === "/schedules") {
      if (!authorized(request, env)) return json({ error: "unauthorized" }, 401);
      try {
        const params = validateSchedule(await request.json() as ScheduleParams);
        const id = await instanceId(params);
        let existing = false;
        try {
          await env.PUBLISH_SCHEDULES.get(id);
          existing = true;
        } catch (error) {
          if (!String(error).includes("instance.not_found")) throw error;
        }
        if (existing) return json({ instance_id: id, status: "waiting", ...params });
        await env.PUBLISH_SCHEDULES.create({ id, params });
        return json({ instance_id: id, status: "waiting", ...params }, 202);
      } catch (error) {
        return json({ error: error instanceof Error ? error.message : "invalid_request" }, 400);
      }
    }
    return new Response("not found", { status: 404 });
  },
};

function validateSchedule(value: ScheduleParams): ScheduleParams {
  const required = ["content_id", "scheduled_time", "latest_publish_time", "snapshot_repo", "snapshot_commit", "snapshot_path", "trace_id"] as const;
  for (const key of required) if (!value?.[key]) throw new Error(`${key} is required`);
  if (!Number.isInteger(value.content_version) || value.content_version < 1) throw new Error("content_version must be a positive integer");
  const scheduled = Date.parse(value.scheduled_time);
  const latest = Date.parse(value.latest_publish_time);
  if (Number.isNaN(scheduled) || !value.scheduled_time.match(/[+-]\d\d:\d\d|Z$/)) throw new Error("scheduled_time must be ISO 8601 with timezone");
  if (Number.isNaN(latest) || latest <= scheduled) throw new Error("latest_publish_time must be later than scheduled_time");
  if (scheduled - Date.now() < MIN_LEAD_MS) throw new Error("scheduled_time must be at least five minutes in the future");
  return value;
}

async function instanceId(params: ScheduleParams): Promise<string> {
  const bytes = new TextEncoder().encode(`${params.content_id}:${params.content_version}:${params.scheduled_time}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return `publish-${[...new Uint8Array(digest)].map((x) => x.toString(16).padStart(2, "0")).join("").slice(0, 32)}`;
}

async function dispatchGitHub(env: Env, params: ScheduleParams): Promise<boolean> {
  const payload = { event_type: env.GITHUB_EVENT_TYPE || DEFAULT_EVENT_TYPE, client_payload: params };
  for (let attempt = 1; attempt <= MAX_DISPATCH_ATTEMPTS; attempt++) {
    const response = await fetch(`https://api.github.com/repos/${env.GITHUB_REPOSITORY}/dispatches`, {
      method: "POST",
      headers: { Authorization: `Bearer ${env.GITHUB_PAT}`, Accept: "application/vnd.github+json", "User-Agent": "threads-publish-scheduler", "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (response.ok) return true;
    if (attempt < MAX_DISPATCH_ATTEMPTS) await new Promise((resolve) => setTimeout(resolve, attempt * 1000));
  }
  return false;
}

async function createIssue(env: Env, params: ScheduleParams, kind: string, detail: string) {
  await fetch(`https://api.github.com/repos/${env.GITHUB_REPOSITORY}/issues`, {
    method: "POST",
    headers: { Authorization: `Bearer ${env.GITHUB_PAT}`, Accept: "application/vnd.github+json", "User-Agent": "threads-publish-scheduler", "Content-Type": "application/json" },
    body: JSON.stringify({ title: `[publish-alert] ${kind}: ${params.content_id} v${params.content_version}`, labels: ["publish-alert"], body: `${detail}\n\ncontent_id: ${params.content_id}\ncontent_version: ${params.content_version}\nscheduled_time: ${params.scheduled_time}\nlatest_publish_time: ${params.latest_publish_time}\nsnapshot_commit: ${params.snapshot_commit}\nsnapshot_path: ${params.snapshot_path}\ntrace_id: ${params.trace_id}\nretry_allowed: false` }),
  });
}

function authorized(request: Request, env: Env) { return request.headers.get("Authorization") === `Bearer ${env.SCHEDULER_API_TOKEN}`; }
function json(value: unknown, status = 200) { return new Response(JSON.stringify(value), { status, headers: { "content-type": "application/json" } }); }
