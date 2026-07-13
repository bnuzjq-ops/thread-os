import test from 'node:test';
import assert from 'node:assert/strict';
import {dispatchMonitor} from '../reply_scheduler_worker.mjs';

test('scheduler dispatches the monitor repository event', async () => {
  let request;
  const result = await dispatchMonitor({
    env: {GITHUB_REPO: 'bnuzjq-ops/thread-os', GITHUB_PAT: 'test-pat'},
    fetchImpl: async (url, init) => {
      request = {url, init};
      return new Response(null, {status: 204});
    },
  });
  assert.deepEqual(result, {repo: 'bnuzjq-ops/thread-os', eventType: 'threads_reply_monitor'});
  assert.equal(request.url, 'https://api.github.com/repos/bnuzjq-ops/thread-os/dispatches');
  assert.equal(request.init.headers.Authorization, 'Bearer test-pat');
  assert.deepEqual(JSON.parse(request.init.body), {
    event_type: 'threads_reply_monitor',
    client_payload: {source: 'cloudflare_cron_scheduler'},
  });
});

test('scheduler rejects missing credentials', async () => {
  await assert.rejects(() => dispatchMonitor({env: {}}), /Missing GITHUB_REPO/);
});
