import { Router } from 'express';
import { readFileSync, unlinkSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import ffmpeg from 'fluent-ffmpeg';

export function makeSignRoute({ sidecar, clipCache, wordmapPath }) {
  const router = Router();

  router.post('/', async (req, res) => {
    try {
      const { text } = req.body || {};
      if (!text || typeof text !== 'string') {
        return res.status(400).json({ status: 'error', message: 'text is required' });
      }

      const glossTokens = await sidecar.gloss({ text, language: 'en' });
      const wordmap = JSON.parse(readFileSync(wordmapPath, 'utf8'));

      const clipPaths = [];
      const missing = [];
      for (const g of glossTokens) {
        const entry = wordmap[g.gloss];
        if (!entry) { missing.push(g.gloss); continue; }
        const p = await clipCache.get(g.gloss, entry.clip_url);
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
