const DEFAULT_EVENT_TYPE = 'threads_reply_monitor';

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {'content-type': 'application/json; charset=utf-8'},
  });
}

function required(env, name) {
  const value = String(env?.[name] ?? '').trim();
  if (!value) throw new Error(`Missing ${name}`);
  return value;
}

export async function dispatchMonitor({fetchImpl = globalThis.fetch, env = {}} = {}) {
  const repo = required(env, 'GITHUB_REPO');
  const pat = required(env, 'GITHUB_PAT');
  const eventType = String(env.GITHUB_DISPATCH_EVENT ?? DEFAULT_EVENT_TYPE).trim();
  const response = await fetchImpl(`https://api.github.com/repos/${repo}/dispatches`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${pat}`,
      Accept: 'application/vnd.github+json',
      'Content-Type': 'application/json',
      'User-Agent': 'threads-reply-scheduler',
      'X-GitHub-Api-Version': '2022-11-28',
    },
    body: JSON.stringify({
      event_type: eventType,
      client_payload: {source: 'cloudflare_cron_scheduler'},
    }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`GitHub dispatch failed with status ${response.status}${detail ? `: ${detail}` : ''}`);
  }
  return {repo, eventType};
}

export default {
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(dispatchMonitor({env}));
  },
  async fetch(request) {
    if (request.method !== 'GET') return jsonResponse({error: 'method not allowed'}, 405);
    return jsonResponse({ok: true, scheduler: 'threads-reply-monitor'});
  },
};
