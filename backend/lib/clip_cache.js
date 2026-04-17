import { createHash } from 'node:crypto';
import { createWriteStream, existsSync, mkdirSync, renameSync } from 'node:fs';
import { join } from 'node:path';
import { pipeline } from 'node:stream/promises';
import { request } from 'undici';

export class ClipFetchError extends Error {
  constructor(status, url) {
    super(`ClipFetchError: ${status} for ${url}`);
    this.status = status;
    this.url = url;
  }
}

export class ClipCache {
  constructor(cacheDir) {
    this.cacheDir = cacheDir;
    if (!existsSync(cacheDir)) mkdirSync(cacheDir, { recursive: true });
  }

  #pathFor(id) {
    const hash = createHash('sha1').update(id).digest('hex');
    return join(this.cacheDir, `${hash}.mp4`);
  }

  async get(id, url) {
    const finalPath = this.#pathFor(id);
    if (existsSync(finalPath)) return finalPath;

    const tmpPath = `${finalPath}.tmp-${process.pid}-${Date.now()}`;
    const { statusCode, body } = await request(url);
    if (statusCode >= 400) {
      body.dump();
      throw new ClipFetchError(statusCode, url);
    }
    await pipeline(body, createWriteStream(tmpPath));
    renameSync(tmpPath, finalPath);
    return finalPath;
  }
}
