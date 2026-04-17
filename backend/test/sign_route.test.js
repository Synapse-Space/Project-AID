import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createServer } from 'node:http';
import express from 'express';
import { MockAgent, setGlobalDispatcher } from 'undici';

import { makeSignRoute } from '../routes/sign.js';
import { SidecarClient } from '../lib/sidecar_client.js';
import { ClipCache } from '../lib/clip_cache.js';

let clipServer;
let clipBaseUrl;
let cacheDir;
let wordmapPath;

before(async () => {
  cacheDir = mkdtempSync(join(tmpdir(), 'signtest-'));

  const mp4 = readFileSync(new URL('./fixtures/black_1s.mp4', import.meta.url));
  clipServer = createServer((req, res) => {
    res.writeHead(200, { 'content-type': 'video/mp4' });
    res.end(mp4);
  });
  await new Promise((r) => clipServer.listen(0, r));
  clipBaseUrl = `http://127.0.0.1:${clipServer.address().port}`;

  wordmapPath = join(cacheDir, 'wordmap.json');
  writeFileSync(wordmapPath, JSON.stringify({
    I:     { clip_url: `${clipBaseUrl}/i.mp4`,     source: 'test' },
    WATER: { clip_url: `${clipBaseUrl}/water.mp4`, source: 'test' },
    DRINK: { clip_url: `${clipBaseUrl}/drink.mp4`, source: 'test' },
  }));
});

after(() => {
  clipServer.close();
  rmSync(cacheDir, { recursive: true, force: true });
});

test('POST /sign returns MP4 for "I drink water."', async () => {
  const mock = new MockAgent();
  mock.disableNetConnect();
  setGlobalDispatcher(mock);
  const pool = mock.get('http://127.0.0.1:8090');
  pool.intercept({ path: '/gloss', method: 'POST' }).reply(200, {
    gloss: [
      { gloss: 'I',     kind: 'sign', source_text: 'I' },
      { gloss: 'WATER', kind: 'sign', source_text: 'water' },
      { gloss: 'DRINK', kind: 'sign', source_text: 'drink' },
    ],
  });

  const app = express();
  app.use(express.json());
  app.use('/sign', makeSignRoute({
    sidecar:    new SidecarClient('http://127.0.0.1:8090'),
    clipCache:  new ClipCache(cacheDir),
    wordmapPath,
  }));

  const server = app.listen(0);
  try {
    const { port } = server.address();
    // Whitelist the local test server since MockAgent.disableNetConnect() also blocks it
    mock.enableNetConnect(`127.0.0.1:${port}`);
    // The clip HTTP server is also real HTTP — whitelist it too
    mock.enableNetConnect(new URL(clipBaseUrl).host);

    const resp = await fetch(`http://127.0.0.1:${port}/sign`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ text: 'I drink water.' }),
    });
    assert.equal(resp.status, 200);
    assert.equal(resp.headers.get('content-type'), 'video/mp4');
    const buf = Buffer.from(await resp.arrayBuffer());
    assert.ok(buf.length > 0);
  } finally {
    server.close();
  }
});
