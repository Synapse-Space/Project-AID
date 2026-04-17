import { test } from 'node:test';
import assert from 'node:assert/strict';
import { MockAgent, setGlobalDispatcher } from 'undici';

import { SidecarClient } from '../lib/sidecar_client.js';

test('transcribe POSTs audio and returns text', async () => {
  const mock = new MockAgent();
  mock.disableNetConnect();
  setGlobalDispatcher(mock);

  const pool = mock.get('http://127.0.0.1:8090');
  pool.intercept({ path: '/transcribe', method: 'POST' })
      .reply(200, { text: 'hello world', language_detected: 'en' });

  const client = new SidecarClient('http://127.0.0.1:8090');
  const result = await client.transcribe({
    audioBase64: 'AAAA',
    mimeType: 'audio/webm',
    language: 'en',
  });

  assert.equal(result.text, 'hello world');
  assert.equal(result.languageDetected, 'en');
});

test('gloss POSTs text and returns gloss tokens', async () => {
  const mock = new MockAgent();
  mock.disableNetConnect();
  setGlobalDispatcher(mock);

  const pool = mock.get('http://127.0.0.1:8090');
  pool.intercept({ path: '/gloss', method: 'POST' })
      .reply(200, {
        gloss: [
          { gloss: 'TOMORROW', kind: 'sign', source_text: 'tomorrow' },
          { gloss: 'SCHOOL', kind: 'sign', source_text: 'school' },
          { gloss: 'GO', kind: 'sign', source_text: 'going' },
        ],
      });

  const client = new SidecarClient('http://127.0.0.1:8090');
  const result = await client.gloss({ text: 'Going to school tomorrow', language: 'en' });

  assert.equal(result.length, 3);
  assert.equal(result[0].gloss, 'TOMORROW');
});
