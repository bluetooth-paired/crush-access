import assert from 'node:assert/strict';
import { once } from 'node:events';
import { get } from 'node:http';
import test from 'node:test';
import { createAdvisorServer, readConfig } from './server.mjs';

const sampleMessages = [{ role: 'user', content: 'Sample message only.' }];

async function start(t, env = {}, fetchProvider = undefined) {
  const config = readConfig({ PORT: '0', ...env });
  const server = createAdvisorServer(config, fetchProvider);
  server.listen(config.port, config.host);
  t.after(() => server.close());
  await once(server, 'listening');
  return `http://127.0.0.1:${server.address().port}`;
}

function post(url, data, headers = {}) {
  return fetch(`${url}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(data),
  });
}

test('serves the frontend and reports an unconfigured backend without exposing credentials', async t => {
  const url = await start(t);
  const page = await fetch(url);
  assert.equal(page.status, 200);
  assert.match(await page.text(), /<script[^>]+src=/);
  const result = await fetch(`${url}/api/status`);
  assert.deepEqual(await result.json(), {
    configured: false, model: 'deepseek-flash', requiresAccessToken: false,
  });
  assert.equal((await post(url, { messages: sampleMessages })).status, 503);
  assert.equal((await fetch(`${url}/server/server.mjs`)).status, 404);
});

test('validates roles and submits only text fields to the fixed DeepSeek endpoint', async t => {
  let request;
  const url = await start(t, { DEEPSEEK_API_KEY: 'test-key' }, (target, options) => {
    request = { target, options };
    return Response.json({ choices: [{ message: { content: 'Example reply.' } }] });
  });
  assert.equal((await post(url, { messages: [{ role: 'system', content: 'invalid' }] })).status, 400);
  assert.equal(request, undefined);
  const result = await post(url, {
    messages: [{ ...sampleMessages[0], internal: 'discard me' }],
    context: 'Synthetic context.',
    model: 'untrusted-model',
  });
  assert.equal(result.status, 200);
  assert.deepEqual(await result.json(), { reply: 'Example reply.', model: 'deepseek-flash' });
  assert.equal(request.target, 'https://api.deepseek.com/chat/completions');
  assert.equal(request.options.headers.Authorization, 'Bearer test-key');
  const body = JSON.parse(request.options.body);
  assert.deepEqual(body.messages.at(-1), sampleMessages[0]);
  assert.equal(body.messages[0].role, 'system');
  assert.equal(body.messages[1].role, 'user');
  assert.match(body.messages[1].content, /Synthetic context\./);
  assert.equal(body.model, 'deepseek-flash');
  assert.deepEqual(body.thinking, { type: 'disabled' });
});

test('requires a separate access token for public and cross-origin configurations', async t => {
  assert.throws(() => readConfig({ HOST: '0.0.0.0' }), /ADVISOR_ACCESS_TOKEN/);
  assert.throws(() => readConfig({ ADVISOR_ALLOWED_ORIGIN: 'https://example.test' }), /ADVISOR_ACCESS_TOKEN/);
  const accessToken = 'x'.repeat(32);
  const origin = 'https://example.test';
  const url = await start(t, {
    DEEPSEEK_API_KEY: 'test-key', ADVISOR_ACCESS_TOKEN: accessToken, ADVISOR_ALLOWED_ORIGIN: origin,
  }, () => Response.json({ choices: [{ message: { content: 'OK' } }] }));
  const denied = await post(url, { messages: sampleMessages }, { Origin: 'https://other.test' });
  assert.equal(denied.status, 403);
  assert.equal(denied.headers.get('access-control-allow-origin'), null);
  const preflight = await fetch(`${url}/api/chat`, {
    method: 'OPTIONS',
    headers: { Origin: origin, 'Access-Control-Request-Method': 'POST' },
  });
  assert.equal(preflight.status, 204);
  assert.equal(preflight.headers.get('access-control-allow-origin'), origin);
  assert.equal((await post(url, { messages: sampleMessages }, { Origin: origin })).status, 401);
  const result = await post(url, { messages: sampleMessages }, {
    Origin: origin, Authorization: `Bearer ${accessToken}`,
  });
  assert.equal(result.status, 200);
});

test('filters provider failures and rejects oversized requests before calling the model', async t => {
  let calls = 0;
  const url = await start(t, { DEEPSEEK_API_KEY: 'test-key' }, () => {
    calls++;
    return Response.json({ error: { message: 'private upstream error' } }, { status: 429 });
  });
  assert.equal((await post(url, { messages: sampleMessages, context: 'a'.repeat(110_000) })).status, 413);
  assert.equal(calls, 0);
  const result = await post(url, { messages: sampleMessages });
  assert.equal(result.status, 429);
  assert.match((await result.json()).error, /频率/);
  assert.equal(calls, 1);
});

test('rejects malformed bodies, untrusted origins and wrong local hosts', async t => {
  const url = await start(t, { DEEPSEEK_API_KEY: 'test-key' }, () => assert.fail('Provider must not be called'));
  assert.equal((await post(url, { messages: sampleMessages }, { 'Content-Type': 'text/plain' })).status, 415);
  const malformed = await fetch(`${url}/api/chat`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{',
  });
  assert.equal(malformed.status, 400);
  assert.equal((await post(url, { messages: sampleMessages, context: {} })).status, 400);
  assert.equal((await post(url, { messages: [{ role: 'user', content: ' ' }] })).status, 400);
  assert.equal((await fetch(`${url}/app.js`, { method: 'HEAD' })).status, 200);
  assert.equal((await fetch(`${url}/missing.js`)).status, 404);
  assert.equal((await fetch(`${url}/api/chat`)).status, 405);
  const status = await new Promise((fulfill, reject) => {
    const req = get(`${url}/api/status`, { headers: { Host: 'untrusted.test' } }, res => {
      res.resume();
      fulfill(res.statusCode);
    });
    req.on('error', reject);
  });
  assert.equal(status, 403);
});

test('bounds concurrent requests and allows a new request when work completes', async t => {
  let active = 0;
  let onThreeRequests;
  const threeRequests = new Promise(fulfill => { onThreeRequests = fulfill; });
  let respond;
  const release = new Promise(fulfill => { respond = fulfill; });
  const url = await start(t, { DEEPSEEK_API_KEY: 'test-key' }, async () => {
    if (++active === 3) onThreeRequests();
    await release;
    return Response.json({ choices: [{ message: { content: 'OK' } }] });
  });
  const pending = Array.from({ length: 3 }, () => post(url, { messages: sampleMessages }));
  try {
    await threeRequests;
    assert.equal((await post(url, { messages: sampleMessages })).status, 429);
  } finally {
    respond();
  }
  const responses = await Promise.all(pending);
  assert.ok(responses.every(response => response.status === 200));
  assert.equal((await post(url, { messages: sampleMessages })).status, 200);
});
