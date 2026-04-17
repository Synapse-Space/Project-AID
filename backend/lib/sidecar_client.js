import { request } from 'undici';

export class SidecarError extends Error {
  constructor(status, body) {
    super(`sidecar ${status}: ${JSON.stringify(body)}`);
    this.status = status;
    this.body = body;
  }
}

export class SidecarClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  async #post(path, body) {
    const { statusCode, body: respBody } = await request(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    });
    const json = await respBody.json();
    if (statusCode >= 400) throw new SidecarError(statusCode, json);
    return json;
  }

  async transcribe({ audioBase64, mimeType, language = 'auto' }) {
    const resp = await this.#post('/transcribe', {
      audio_base64: audioBase64,
      mime_type: mimeType,
      language,
    });
    return { text: resp.text, languageDetected: resp.language_detected };
  }

  async gloss({ text, language = 'en' }) {
    const resp = await this.#post('/gloss', { text, language });
    return resp.gloss;
  }
}
