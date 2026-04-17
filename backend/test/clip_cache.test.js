import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, existsSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createServer } from 'node:http';

import { ClipCache } from '../lib/clip_cache.js';

let httpServer;
let baseUrl;
let cacheDir;

before(async () => {
  cacheDir = mkdtempSync(join(tmpdir(), 'clipcache-'));
  httpServer = createServer((req, res) => {
    if (req.url === '/ok.mp4') {
      res.writeHead(200, { 'content-type': 'video/mp4' });
      res.end(Buffer.from([0, 1, 2, 3, 4, 5, 6, 7]));
    } else {
      res.writeHead(404).end();
    }
  });
  await new Promise((r) => httpServer.listen(0, r));
  baseUrl = `http://127.0.0.1:${httpServer.address().port}`;
});

after(() => {
  httpServer.close();
  rmSync(cacheDir, { recursive: true, force: true });
});

test('first fetch writes file; second hit serves from cache', async () => {
  const cache = new ClipCache(cacheDir);
  const id = 'school';

  const p1 = await cache.get(id, `${baseUrl}/ok.mp4`);
  assert.ok(existsSync(p1), 'file should exist after first get');
  const contents = readFileSync(p1);
  assert.equal(contents.length, 8);

  // Mutate the file so we can prove the second call is cached (no re-download).
  writeFileSync(p1, Buffer.from('CACHED'));

  const p2 = await cache.get(id, `${baseUrl}/ok.mp4`);
  assert.equal(p1, p2);
  assert.equal(readFileSync(p2).toString(), 'CACHED');
});

test('404 raises ClipFetchError', async () => {
  const cache = new ClipCache(cacheDir);
  await assert.rejects(
    () => cache.get('missing', `${baseUrl}/missing.mp4`),
    /ClipFetchError.*404/,
  );
});
