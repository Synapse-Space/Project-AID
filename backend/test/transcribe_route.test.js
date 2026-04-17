import { test } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { MockAgent, setGlobalDispatcher } from 'undici';

import { makeTranscribeRoute } from '../routes/transcribe.js';
import { SidecarClient } from '../lib/sidecar_client.js';

async function startServer(app) {
  return new Promise((resolve) => {
    const server = app.listen(0, () => resolve({ server, port: server.address().port }));
  });
}

test('POST /transcribe proxies to sidecar and returns text', async () => {
  const mock = new MockAgent();
  mock.disableNetConnect();
  setGlobalDispatcher(mock);
  const pool = mock.get('http://127.0.0.1:8090');
  pool.intercept({ path: '/transcribe', method: 'POST' })
      .reply(200, { text: 'hello', language_detected: 'en' });

  const app = express();
  app.use(express.json({ limit: '25mb' }));
  app.use('/transcribe', makeTranscribeRoute(new SidecarClient('http://127.0.0.1:8090')));

  const { server, port } = await startServer(app);
  // Allow the test's fetch() to reach the ephemeral local server; only the
  // sidecar origin should be intercepted.
  mock.enableNetConnect(`127.0.0.1:${port}`);
  try {
    const resp = await fetch(`http://127.0.0.1:${port}/transcribe`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ audioBase64: 'AAAA', mimeType: 'audio/webm' }),
    });
    assert.equal(resp.status, 200);
    const body = await resp.json();
    assert.equal(body.status, 'success');
    assert.equal(body.text, 'hello');
  } finally {
    server.close();
  }
});
