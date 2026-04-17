import { Router } from 'express';

export function makeTranscribeRoute(sidecar) {
  const router = Router();

  router.post('/', async (req, res) => {
    try {
      const { audioBase64, mimeType = 'audio/webm', language = 'auto' } = req.body || {};
      if (!audioBase64) {
        return res.status(400).json({ status: 'error', message: 'audioBase64 is required' });
      }
      const result = await sidecar.transcribe({ audioBase64, mimeType, language });
      return res.json({ status: 'success', text: result.text, language: result.languageDetected });
    } catch (e) {
      return res.status(502).json({ status: 'error', message: e.message });
    }
  });

  return router;
}
