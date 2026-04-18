import { Router } from 'express';
import { readFileSync, unlinkSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import ffmpeg from 'fluent-ffmpeg';

export function makeSignRoute({ sidecar, clipCache, wordmapPath }) {
  const router = Router();

  let cachedWordmap = null;
  let cachedPhraseIndex = null;
  function loadWordmap() {
    if (cachedWordmap) return { wordmap: cachedWordmap, phraseIndex: cachedPhraseIndex };
    const wordmap = JSON.parse(readFileSync(wordmapPath, 'utf8'));
    const phraseIndex = new Map();
    for (const key of Object.keys(wordmap)) {
      for (const word of key.toLowerCase().split(/\s+/)) {
        if (!phraseIndex.has(word)) phraseIndex.set(word, key);
      }
    }
    cachedWordmap = wordmap;
    cachedPhraseIndex = phraseIndex;
    return { wordmap, phraseIndex };
  }

  function resolveGloss(g, wordmap, phraseIndex) {
    const candidates = [g.gloss, g.gloss?.toLowerCase(), g.source_text?.toLowerCase()].filter(Boolean);
    for (const c of candidates) {
      if (wordmap[c]) return { key: c, entry: wordmap[c] };
    }
    for (const c of candidates) {
      const phraseKey = phraseIndex.get(c);
      if (phraseKey) return { key: phraseKey, entry: wordmap[phraseKey] };
    }
    return null;
  }

  router.post('/', async (req, res) => {
    try {
      const { text } = req.body || {};
      if (!text || typeof text !== 'string') {
        return res.status(400).json({ status: 'error', message: 'text is required' });
      }

      const glossTokens = await sidecar.gloss({ text, language: 'en' });
      const { wordmap, phraseIndex } = loadWordmap();

      const clipPaths = [];
      const missing = [];
      for (const g of glossTokens) {
        const hit = resolveGloss(g, wordmap, phraseIndex);
        if (!hit) { missing.push(g.gloss); continue; }
        const p = await clipCache.get(hit.key, hit.entry.clip_url);
        clipPaths.push(p);
      }
      if (clipPaths.length === 0) {
        return res.status(422).json({ status: 'error', message: 'no clips matched', missing });
      }

      const listPath = join(tmpdir(), `concat-${Date.now()}.txt`);
      writeFileSync(listPath, clipPaths.map((p) => `file '${p.replace(/'/g, "'\\''")}'`).join('\n'));

      const outPath = join(tmpdir(), `out-${Date.now()}.mp4`);

      await new Promise((resolve, reject) => {
        ffmpeg()
          .input(listPath)
          .inputOptions(['-f concat', '-safe 0'])
          .outputOptions(['-c', 'copy', '-movflags', '+faststart'])
          .on('end', resolve)
          .on('error', reject)
          .save(outPath);
      });

      const buf = readFileSync(outPath);
      unlinkSync(listPath);
      unlinkSync(outPath);

      res.setHeader('content-type', 'video/mp4');
      if (missing.length) res.setHeader('x-missing-glosses', JSON.stringify(missing));
      res.status(200).send(buf);
    } catch (e) {
      res.status(500).json({ status: 'error', message: e.message });
    }
  });

  return router;
}
