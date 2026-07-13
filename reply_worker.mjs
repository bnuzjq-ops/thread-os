const FEISHU_SUCCESS_TOAST = {
  toast: {
    type: 'success',
    content: '收到，已转入处理。',
  },
};

function normalizePathname(pathname) {
  if (!pathname || pathname === '/') {
    return '/';
  }
  return pathname.replace(/\/+$/, '') || '/';
}

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
    },
  });
}

function textResponse(body, status = 200) {
  return new Response(body, {
    status,
    headers: {
      'content-type': 'text/plain; charset=utf-8',
    },
  });
}

async function sha256Hex(text) {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) {
    throw new Error('Web Crypto is unavailable');
  }

  const digest = await subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
}

export async function computeFeishuSignature({ timestamp, nonce, token, body }) {
  return sha256Hex(`${timestamp}${nonce}${token}${body}`);
}

export function parseReplyActionValue(raw) {
  let value = '';
  if (typeof raw === 'string') {
    value = raw.trim();
  } else if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
    const command = typeof raw.action === 'string' ? raw.action.trim() : '';
    const replyTaskId = typeof raw.reply_task_id === 'string' ? raw.reply_task_id.trim() : '';
    if (command && replyTaskId) {
      value = `${command}:${replyTaskId}`;
    }
  }

  if (!value) {
    throw new Error('Reply action value must be a non-empty string or object');
  }

  const parts = value.split(':');
  if (parts.length < 3) {
    throw new Error(`Invalid reply action value: ${raw}`);
  }

  const [command, taskKind, ...rest] = parts;
  const commentId = rest.join(':');

  if (!command || !taskKind || !commentId) {
    throw new Error(`Invalid reply action value: ${raw}`);
  }

  return {
    command,
    raw: value,
    taskId: `${taskKind}:${commentId}`,
    taskKind,
    commentId,
  };
}

function extractActionValue(payload) {
  const candidates = [
    payload?.action?.value,
    payload?.action?.data?.value,
    payload?.event?.action?.value,
    payload?.card?.action?.value,
    payload?.data?.action?.value,
    payload?.value,
  ];

  return (
    candidates.find((candidate) => {
      if (typeof candidate === 'string') {
        return candidate.trim();
      }
      return candidate && typeof candidate === 'object' && !Array.isArray(candidate);
    }) ?? null
  );
}

function extractMessageId(payload) {
  const candidates = [
    payload?.message?.message_id,
    payload?.message?.messageId,
    payload?.event?.message?.message_id,
    payload?.event?.message?.messageId,
    payload?.context?.message_id,
    payload?.context?.messageId,
    payload?.data?.message_id,
    payload?.data?.messageId,
  ];

  return (
    candidates.find((candidate) => typeof candidate === 'string' && candidate.trim())?.trim() ??
    ''
  );
}

function readHeader(headers, name) {
  return headers.get(name) ?? headers.get(name.toLowerCase()) ?? '';
}

async function verifyFeishuSignature(request, bodyText, verificationToken, payload = null) {
  const timestamp = readHeader(request.headers, 'x-lark-request-timestamp');
  const nonce = readHeader(request.headers, 'x-lark-request-nonce');
  const signature = readHeader(request.headers, 'x-lark-signature');
  const normalizedToken = String(verificationToken ?? '').trim();

  if (!normalizedToken) {
    return {
      ok: false,
      status: 500,
      error: 'Missing FEISHU_VERIFICATION_TOKEN',
    };
  }

  if (!timestamp || !nonce || !signature) {
    if (payload && typeof payload.token === 'string' && payload.token.trim() === normalizedToken) {
      return { ok: true, mode: 'body-token' };
    }
    return { ok: false, status: 401, error: 'Missing Feishu signature headers' };
  }

  const expectedSignature = await computeFeishuSignature({
    timestamp,
    nonce,
    token: normalizedToken,
    body: bodyText,
  });

  if (expectedSignature !== signature) {
    return {
      ok: false,
      status: 401,
      error: 'Invalid Feishu signature',
    };
  }

  return { ok: true };
}

async function dispatchToGithub({ fetchImpl, repo, pat, eventType, payload }) {
  const response = await fetchImpl(`https://api.github.com/repos/${repo}/dispatches`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${pat}`,
      'User-Agent': 'threads-reply-worker',
      Accept: 'application/vnd.github+json',
      'Content-Type': 'application/json',
      'X-GitHub-Api-Version': '2022-11-28',
    },
    body: JSON.stringify({
      event_type: eventType,
      client_payload: payload,
    }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(
      `GitHub dispatch failed with status ${response.status}${detail ? `: ${detail}` : ''}`,
    );
  }
}

export async function handleFeishuCallback(request, env = {}, runtime = {}) {
  const url = new URL(request.url);
  const pathname = normalizePathname(url.pathname);

  if (pathname === '/health') {
    return textResponse('ok');
  }

  if (pathname !== '/feishu/callback') {
    return jsonResponse({ error: 'not found' }, 404);
  }

  if (request.method !== 'POST') {
    return jsonResponse({ error: 'method not allowed' }, 405);
  }

  const bodyText = await request.text();
  let payload;
  try {
    payload = JSON.parse(bodyText);
  } catch {
    return jsonResponse({ error: 'invalid json' }, 400);
  }

  const verification = await verifyFeishuSignature(
    request,
    bodyText,
    env.FEISHU_VERIFICATION_TOKEN,
    payload,
  );

  if (!verification.ok) {
    return jsonResponse({ error: verification.error }, verification.status);
  }

  if (payload?.challenge) {
    return jsonResponse({ challenge: payload.challenge });
  }

  const actionValue = extractActionValue(payload);
  if (!actionValue) {
    return jsonResponse({ error: 'missing action value' }, 400);
  }

  const action = parseReplyActionValue(actionValue);
  const repo = String(env.GITHUB_REPO ?? '').trim();
  const pat = String(env.GITHUB_PAT ?? '').trim();
  const eventType = String(env.GITHUB_DISPATCH_EVENT ?? 'threads_reply_action').trim();

  if (!repo) {
    return jsonResponse({ error: 'Missing GITHUB_REPO' }, 500);
  }

  if (!pat) {
    return jsonResponse({ error: 'Missing GITHUB_PAT' }, 500);
  }

  const payloadForDispatch = {
    action: action.command,
    action_value: action.raw,
    comment_id: action.commentId,
    message_id: extractMessageId(payload),
    reply_task_id: action.taskId,
    source: 'feishu_card_callback',
    task_kind: action.taskKind,
  };
  if (payload?.dry_run === true) {
    payloadForDispatch.dry_run = true;
  }

  const fetchImpl = runtime.fetch ?? globalThis.fetch.bind(globalThis);
  try {
    await dispatchToGithub({
      fetchImpl,
      repo,
      pat,
      eventType,
      payload: payloadForDispatch,
    });
  } catch (error) {
    return jsonResponse(
      {
        error: 'github dispatch failed',
        detail: error instanceof Error ? error.message : String(error),
      },
      502,
    );
  }

  return jsonResponse(FEISHU_SUCCESS_TOAST);
}

export default {
  fetch(request, env, ctx) {
    return handleFeishuCallback(request, env, {
      fetch: globalThis.fetch,
      ctx,
    });
  },
};
