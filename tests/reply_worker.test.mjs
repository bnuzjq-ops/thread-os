import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import test from 'node:test';

import {
  computeFeishuSignature,
  handleFeishuCallback,
  parseReplyActionValue,
} from '../reply_worker.mjs';

test('computeFeishuSignature matches the Feishu callback scheme', async () => {
  const timestamp = '1700000000';
  const nonce = 'nonce-1';
  const token = 'verification-token';
  const body = '{"action":{"value":"send:reply:comment-2"}}';

  const expected = crypto
    .createHash('sha256')
    .update(`${timestamp}${nonce}${token}${body}`, 'utf8')
    .digest('hex');

  await assert.equal(
    await computeFeishuSignature({ timestamp, nonce, token, body }),
    expected,
  );
});

test('parseReplyActionValue splits the command and task id', () => {
  assert.deepEqual(parseReplyActionValue('send:reply:comment-2'), {
    command: 'send',
    raw: 'send:reply:comment-2',
    taskId: 'reply:comment-2',
    taskKind: 'reply',
    commentId: 'comment-2',
  });
});

test('parseReplyActionValue accepts Feishu card value objects', () => {
  assert.deepEqual(
    parseReplyActionValue({
      action: 'send',
      reply_task_id: 'reply:comment-2',
    }),
    {
      command: 'send',
      raw: 'send:reply:comment-2',
      taskId: 'reply:comment-2',
      taskKind: 'reply',
      commentId: 'comment-2',
    },
  );
});

test('handleFeishuCallback dispatches a valid card action to GitHub', async () => {
  const body = JSON.stringify({
    action: {
      value: {
        action: 'send',
        reply_task_id: 'reply:comment-2',
      },
    },
    message: {
      message_id: 'om_123',
    },
  });

  const timestamp = '1700000000';
  const nonce = 'nonce-1';
  const verificationToken = 'verification-token';
  const signature = await computeFeishuSignature({
    timestamp,
    nonce,
    token: verificationToken,
    body,
  });

  const requests = [];
  const fetchImpl = async (url, init) => {
    requests.push({ url, init });
    return new Response(null, { status: 204 });
  };

  const response = await handleFeishuCallback(
    new Request('https://jqxblue.cc/feishu/callback', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-lark-request-timestamp': timestamp,
        'x-lark-request-nonce': nonce,
        'x-lark-signature': signature,
      },
      body,
    }),
    {
      FEISHU_VERIFICATION_TOKEN: ` ${verificationToken}\n`,
      GITHUB_DISPATCH_EVENT: 'threads_reply_action',
      GITHUB_PAT: 'github-pat',
      GITHUB_REPO: 'bnuzjq-ops/thread-os',
    },
    { fetch: fetchImpl },
  );

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    toast: {
      type: 'success',
      content: '收到，已转入处理。',
    },
  });

  assert.equal(requests.length, 1);
  assert.equal(
    requests[0].url,
    'https://api.github.com/repos/bnuzjq-ops/thread-os/dispatches',
  );
  assert.equal(requests[0].init.method, 'POST');
  assert.equal(
    requests[0].init.headers.Authorization,
    'Bearer github-pat',
  );
  assert.equal(
    requests[0].init.headers['User-Agent'],
    'threads-reply-worker',
  );

  const dispatchBody = JSON.parse(requests[0].init.body);
  assert.deepEqual(dispatchBody, {
    event_type: 'threads_reply_action',
    client_payload: {
      action: 'send',
      action_value: 'send:reply:comment-2',
      comment_id: 'comment-2',
      message_id: 'om_123',
      reply_task_id: 'reply:comment-2',
      source: 'feishu_card_callback',
      task_kind: 'reply',
    },
  });
});

test('handleFeishuCallback accepts the current card callback body token', async () => {
  const body = JSON.stringify({
    token: 'verification-token',
    action: { value: { action: 'skip', reply_task_id: 'reply:comment-2' } },
  });
  const requests = [];
  const response = await handleFeishuCallback(
    new Request('https://jqxblue.cc/feishu/callback', { method: 'POST', body }),
    {
      FEISHU_VERIFICATION_TOKEN: 'verification-token',
      GITHUB_DISPATCH_EVENT: 'threads_reply_action',
      GITHUB_PAT: 'github-pat',
      GITHUB_REPO: 'bnuzjq-ops/thread-os',
    },
    {
      fetch: async (url, init) => {
        requests.push({ url, init });
        return new Response(null, { status: 204 });
      },
    },
  );

  assert.equal(response.status, 200);
  assert.equal(requests.length, 1);
  assert.equal(JSON.parse(requests[0].init.body).client_payload.action, 'skip');
});

test('handleFeishuCallback returns a challenge response when Feishu verifies the URL', async () => {
  const body = JSON.stringify({
    challenge: 'challenge-token',
    token: 'verification-token',
  });

  const timestamp = '1700000000';
  const nonce = 'nonce-2';
  const verificationToken = 'verification-token';
  const signature = await computeFeishuSignature({
    timestamp,
    nonce,
    token: verificationToken,
    body,
  });

  const response = await handleFeishuCallback(
    new Request('https://jqxblue.cc/feishu/callback', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-lark-request-timestamp': timestamp,
        'x-lark-request-nonce': nonce,
        'x-lark-signature': signature,
      },
      body,
    }),
    {
      FEISHU_VERIFICATION_TOKEN: verificationToken,
      GITHUB_DISPATCH_EVENT: 'threads_reply_action',
      GITHUB_PAT: 'github-pat',
      GITHUB_REPO: 'bnuzjq-ops/thread-os',
    },
    {
      fetch: async () => {
        throw new Error('dispatch should not run during challenge verification');
      },
    },
  );

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { challenge: 'challenge-token' });
});
