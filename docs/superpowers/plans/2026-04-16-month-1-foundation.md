# Project-AID Month 1: Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the ASL/AssemblyAI stack with an ISL-based, open-source, CPU-only pipeline that takes English text and produces a recognisable ISL video. Exit gate: "I am going to school tomorrow" → stitched ISLRTC clips in correct SOV order, rendered as MP4.

**Architecture:** Chrome extension unchanged. Node/Express backend gains an HTTP client to a new Python FastAPI sidecar that owns ASR + NLP + gloss rewriting. ISL clip library replaces WLASL, served through a streaming-cache layer.

**Tech Stack:** Python 3.11, FastAPI, faster-whisper (Whisper via CTranslate2, CPU), spaCy (en_core_web_sm), PyYAML, pytest for the sidecar. Node 20+ `node:test`, Express, fluent-ffmpeg on the backend. ISLRTC dictionary as the clip source.

**Scope note:** This is the Month 1 plan only (Weeks 1–4 of the 4-month spec). Months 2–4 get their own plans written as each prior month ships. Every task below is TDD: failing test first, minimal implementation, passing test, commit.

**Note on "whisper.cpp" in the spec:** The spec names whisper.cpp as the CPU Whisper runtime. In implementation we use **faster-whisper** (CTranslate2 backend, same Whisper weights, MIT). It installs cleanly on all platforms via pip, whereas `pywhispercpp` has recurring build issues. Functionally identical from the sidecar's perspective. Backend swap later is a one-file change in `app/asr.py`.

---

## File structure (what gets created / changed in Month 1)

### New: Python sidecar (`python-sidecar/`)

| Path | Responsibility |
|---|---|
| `python-sidecar/pyproject.toml` | Deps, entrypoint, tool config |
| `python-sidecar/README.md` | Dev setup instructions |
| `python-sidecar/.python-version` | Pin to 3.11 |
| `python-sidecar/app/__init__.py` | Package marker |
| `python-sidecar/app/main.py` | FastAPI app, routes `/health`, `/transcribe`, `/parse`, `/gloss` |
| `python-sidecar/app/asr.py` | `transcribe(audio_bytes, language) -> str` via faster-whisper |
| `python-sidecar/app/parse.py` | `parse(text, lang) -> ParsedClause` via spaCy |
| `python-sidecar/app/gloss.py` | Rule engine: `to_gloss(parsed) -> List[GlossToken]` |
| `python-sidecar/app/models.py` | Pydantic: `ParsedClause`, `GlossToken`, request/response DTOs |
| `python-sidecar/app/rules.yaml` | 15 starter ISL rules (deaf-reviewable) |
| `python-sidecar/tests/__init__.py` | Package marker |
| `python-sidecar/tests/conftest.py` | pytest fixtures (shared spaCy model) |
| `python-sidecar/tests/test_asr.py` | ASR integration tests |
| `python-sidecar/tests/test_parse.py` | Parse correctness tests |
| `python-sidecar/tests/test_gloss.py` | Gloss rule tests (one test per rule) |
| `python-sidecar/tests/fixtures/en_isl_pairs.json` | 50 hand-written English→ISL gold pairs |

### New: Data-prep scripts (`scripts/`)

| Path | Responsibility |
|---|---|
| `scripts/recon_islrtc.py` | Probe ISLRTC site, write `scripts/recon_islrtc_report.md` |
| `scripts/scrape_islrtc.py` | Scrape dictionary entries → `data/islrtc_raw.json` |
| `scripts/build_wordmap.py` | Normalize + build `data/isl_wordmap.json` |

### New: Backend additions (`backend/`)

| Path | Responsibility |
|---|---|
| `backend/lib/sidecar_client.js` | Typed HTTP client for the Python sidecar |
| `backend/lib/clip_cache.js` | Streaming clip fetch + filesystem cache |
| `backend/routes/transcribe.js` | `/transcribe` — proxy to sidecar |
| `backend/routes/sign.js` | `/sign` — text → MP4 end-to-end |
| `backend/test/clip_cache.test.js` | Node `node:test` tests |
| `backend/test/sidecar_client.test.js` | Mocked HTTP client tests |
| `backend/test/sign.test.js` | End-to-end smoke test |

### Modified

| Path | Change |
|---|---|
| `backend/server.js` | Remove AssemblyAI block (38–113). Mount `routes/transcribe.js`, `routes/sign.js`. |
| `backend/.env.example` | Remove AssemblyAI key, add `SIDECAR_URL`, `ISL_CLIP_BASE_URL`, `CLIP_CACHE_DIR`. |
| `.gitignore` | Add `python-sidecar/.venv/`, `python-sidecar/models/`, `data/islrtc_raw.json`, `data/clip_cache/`. |
| `package.json` | Add test script, dotenv dep if missing. |
| `data/wordmap.json` | Move to `data/wordmap_wlasl.archive.json`. Replaced by generated ISL map. |
| `manifest.json` | Update `web_accessible_resources` to reference new wordmap path. |

### Docs

| Path | Responsibility |
|---|---|
| `docs/islrtc_licensing_email.md` | Draft email to `ISLRTC@nic.in` |
| `docs/tester_kickoff.md` | Outreach message + kickoff agenda |

---

## Task 1 — Remove leaked AssemblyAI key

**Files:**
- Modify: `backend/server.js:40`
- Modify: `backend/.env.example`
- Create: `backend/.env` (local, git-ignored)

**Why first:** the key is currently public in git. Even though we swap it out in Task 5, the key must be rotated and stop being read from code *today*.

- [ ] **Step 1: Rotate the key (manual, user action)**

Log into `assemblyai.com` → Settings → API Keys → revoke `95b1e4b1085d4e56ad0c83a3f1262772`. Document the rotation in `docs/SECURITY_INCIDENTS.md` (create if absent) with date and remediation.

- [ ] **Step 2: Update `.env.example` with no secrets**

Replace entire file with:

```bash
# Port for the Node backend
PORT=8080

# Node env
NODE_ENV=development

# URL of the Python sidecar (Task 2)
SIDECAR_URL=http://127.0.0.1:8090

# Where cached ISL clips are stored on disk
CLIP_CACHE_DIR=./data/clip_cache

# ISLRTC source base URL (set after recon in Task 7)
ISL_CLIP_BASE_URL=
```

- [ ] **Step 3: Verify the hardcoded key is gone from `server.js`**

Grep first:

```bash
grep -n "95b1e4b1085d4e56ad0c83a3f1262772" backend/server.js && echo FOUND || echo GONE
```

Expected after Step 4: `GONE`.

- [ ] **Step 4: Delete the entire AssemblyAI block**

Open `backend/server.js`. Delete lines 38–113 inclusive (the whole `app.post('/transcribe', ...)` handler using AssemblyAI). Leave the `require` block, CORS, and the `/stitch` handler intact. We'll re-add `/transcribe` in Task 6 as a sidecar proxy.

- [ ] **Step 5: Add `.env` to `.gitignore` if not already present**

```bash
grep -q "^\.env$" .gitignore || echo ".env" >> .gitignore
```

- [ ] **Step 6: Commit**

```bash
git add backend/server.js backend/.env.example .gitignore
git commit -m "security: remove leaked AssemblyAI key and hardcoded secret

- Delete AssemblyAI /transcribe block from server.js
- Rewrite .env.example with no secrets
- Key rotated on AssemblyAI side (see docs/SECURITY_INCIDENTS.md)
- /transcribe will be re-added in a later task as a sidecar proxy"
```

---

## Task 2 — Scaffold the Python sidecar (FastAPI + health check)

**Files:**
- Create: `python-sidecar/pyproject.toml`
- Create: `python-sidecar/README.md`
- Create: `python-sidecar/.python-version`
- Create: `python-sidecar/app/__init__.py` (empty)
- Create: `python-sidecar/app/main.py`
- Create: `python-sidecar/tests/__init__.py` (empty)
- Create: `python-sidecar/tests/test_health.py`
- Modify: `.gitignore`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "project-aid-sidecar"
version = "0.1.0"
description = "NLP + ASR sidecar for Project-AID"
requires-python = ">=3.11,<3.12"
dependencies = [
    "fastapi==0.115.0",
    "uvicorn[standard]==0.30.6",
    "pydantic==2.9.2",
    "python-multipart==0.0.12",
]

[project.optional-dependencies]
dev = [
    "pytest==8.3.3",
    "httpx==0.27.2",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
markers = [
    "slow: marks tests that download models or hit real ASR (deselect with '-m \"not slow\"')",
]
```

- [ ] **Step 2: Create `.python-version`**

```
3.11
```

- [ ] **Step 3: Create `README.md`**

```markdown
# Project-AID Python Sidecar

FastAPI service providing ASR + NLP + ISL gloss rewriting to the Node backend.

## Setup

```bash
cd python-sidecar
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8090 --reload
```

## Test

```bash
pytest -v
```
```

- [ ] **Step 4: Create minimal `app/main.py` with a health route**

```python
from fastapi import FastAPI

app = FastAPI(title="project-aid-sidecar", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 5: Write the failing health test**

Create `tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 6: Install and run tests — expect PASS**

```bash
cd python-sidecar
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -v
```

Expected: `1 passed`.

- [ ] **Step 7: Update root `.gitignore`**

Append:

```
python-sidecar/.venv/
python-sidecar/__pycache__/
python-sidecar/.pytest_cache/
python-sidecar/**/__pycache__/
python-sidecar/models/
```

- [ ] **Step 8: Commit**

```bash
git add python-sidecar/ .gitignore
git commit -m "feat(sidecar): scaffold FastAPI sidecar with health route

Pins Python 3.11. Adds pyproject.toml, minimal app, and first test.
Next tasks add ASR, parse, and gloss routes."
```

---

## Task 3 — Shared models and sidecar routing shell

**Files:**
- Create: `python-sidecar/app/models.py`
- Modify: `python-sidecar/app/main.py`
- Create: `python-sidecar/tests/test_routing.py`

- [ ] **Step 1: Define the shared DTOs**

Create `app/models.py`:

```python
from typing import Literal

from pydantic import BaseModel, Field

Language = Literal["en", "hi", "auto"]


class TranscribeRequest(BaseModel):
    audio_base64: str
    mime_type: str = "audio/webm"
    language: Language = "auto"


class TranscribeResponse(BaseModel):
    text: str
    language_detected: Language


class ParseRequest(BaseModel):
    text: str
    language: Language = "en"


class ParsedToken(BaseModel):
    text: str
    lemma: str
    pos: str
    dep: str
    head: int = Field(description="Index of syntactic head in the token list")
    is_stop: bool


class ParsedClause(BaseModel):
    tokens: list[ParsedToken]
    language: Language


class ParseResponse(BaseModel):
    clauses: list[ParsedClause]


class GlossToken(BaseModel):
    gloss: str = Field(description="ALL CAPS sign, or FS_<WORD> for fingerspelled")
    kind: Literal["sign", "fingerspell", "paraphrase", "marker"] = "sign"
    source_text: str = Field(description="Original word(s) this gloss came from")


class GlossRequest(BaseModel):
    text: str
    language: Language = "en"


class GlossResponse(BaseModel):
    gloss: list[GlossToken]
```

- [ ] **Step 2: Write failing route-existence tests**

Create `tests/test_routing.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_transcribe_route_exists():
    resp = client.post("/transcribe", json={"audio_base64": "", "mime_type": "audio/webm"})
    assert resp.status_code != 404


def test_parse_route_exists():
    resp = client.post("/parse", json={"text": "hello", "language": "en"})
    assert resp.status_code != 404


def test_gloss_route_exists():
    resp = client.post("/gloss", json={"text": "hello", "language": "en"})
    assert resp.status_code != 404
```

- [ ] **Step 3: Run — expect FAIL**

```bash
pytest tests/test_routing.py -v
```

Expected: all three tests fail with 404.

- [ ] **Step 4: Add route stubs that return 501**

Replace `app/main.py` with:

```python
from fastapi import FastAPI, HTTPException

from app.models import (
    GlossRequest,
    GlossResponse,
    ParseRequest,
    ParseResponse,
    TranscribeRequest,
    TranscribeResponse,
)

app = FastAPI(title="project-aid-sidecar", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/transcribe", response_model=TranscribeResponse)
def transcribe(req: TranscribeRequest) -> TranscribeResponse:
    raise HTTPException(status_code=501, detail="not implemented yet")


@app.post("/parse", response_model=ParseResponse)
def parse(req: ParseRequest) -> ParseResponse:
    raise HTTPException(status_code=501, detail="not implemented yet")


@app.post("/gloss", response_model=GlossResponse)
def gloss(req: GlossRequest) -> GlossResponse:
    raise HTTPException(status_code=501, detail="not implemented yet")
```

- [ ] **Step 5: Run — tests pass (404 gone, 501 is fine)**

```bash
pytest -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add python-sidecar/app/main.py python-sidecar/app/models.py python-sidecar/tests/test_routing.py
git commit -m "feat(sidecar): add typed DTOs and route shells for transcribe/parse/gloss"
```

---

## Task 4 — ASR via faster-whisper

**Files:**
- Modify: `python-sidecar/pyproject.toml`
- Create: `python-sidecar/app/asr.py`
- Create: `python-sidecar/tests/fixtures/hello_world_en.wav`
- Create: `python-sidecar/tests/test_asr.py`
- Modify: `python-sidecar/app/main.py`

- [ ] **Step 1: Add faster-whisper to dependencies**

Edit `pyproject.toml`, add to `[project].dependencies`:

```toml
    "faster-whisper==1.0.3",
```

Install:

```bash
pip install -e ".[dev]"
```

- [ ] **Step 2: Add a tiny sample audio fixture**

Download a ~2-second "hello world" WAV (16 kHz mono) into `tests/fixtures/hello_world_en.wav`. Generate it once locally:

```bash
# macOS: `say -o hello.aiff "hello world"` then convert; or use espeak on Linux:
espeak -w python-sidecar/tests/fixtures/hello_world_en.wav "hello world"
# Fallback: record 2 seconds on any mic, export as 16kHz mono WAV.
```

The fixture is committed to the repo (~100 KB).

- [ ] **Step 3: Write the failing ASR module test**

Create `tests/test_asr.py`:

```python
import base64
from pathlib import Path

import pytest

from app.asr import transcribe

FIXTURE = Path(__file__).parent / "fixtures" / "hello_world_en.wav"


@pytest.mark.slow
def test_transcribe_hello_world():
    audio_bytes = FIXTURE.read_bytes()
    text, lang = transcribe(audio_bytes, mime_type="audio/wav", language="en")
    assert "hello" in text.lower()
    assert lang == "en"
```

- [ ] **Step 4: Run — expect FAIL with ImportError**

```bash
pytest tests/test_asr.py -v
```

Expected: fail on `from app.asr import transcribe`.

- [ ] **Step 5: Implement `app/asr.py`**

```python
"""Whisper ASR using faster-whisper (CTranslate2 backend, CPU)."""

import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Literal

from faster_whisper import WhisperModel

Language = Literal["en", "hi", "auto"]


@lru_cache(maxsize=1)
def _model() -> WhisperModel:
    # `base` = ~142 MB, ~0.3x real-time on CPU for English.
    # `compute_type="int8"` keeps memory low and works everywhere.
    return WhisperModel("base", device="cpu", compute_type="int8")


def transcribe(
    audio_bytes: bytes,
    mime_type: str = "audio/wav",
    language: Language = "auto",
) -> tuple[str, Language]:
    """Transcribe audio bytes, return (text, detected_language)."""
    suffix = ".wav" if mime_type.endswith("wav") else ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_bytes)
        path = Path(f.name)

    try:
        lang_arg = None if language == "auto" else language
        segments, info = _model().transcribe(
            str(path),
            language=lang_arg,
            vad_filter=True,
            beam_size=1,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        detected: Language = info.language if info.language in ("en", "hi") else "auto"
        return text, detected
    finally:
        path.unlink(missing_ok=True)
```

- [ ] **Step 6: Run ASR test — expect PASS**

```bash
pytest tests/test_asr.py -v -m slow
```

Expected: PASS (first run downloads model, ~2 minutes; subsequent runs ~5 seconds).

- [ ] **Step 7: Wire `/transcribe` route to the module**

In `app/main.py`, replace the `transcribe` handler:

```python
import base64

from app.asr import transcribe as asr_transcribe


@app.post("/transcribe", response_model=TranscribeResponse)
def transcribe(req: TranscribeRequest) -> TranscribeResponse:
    audio_bytes = base64.b64decode(req.audio_base64)
    text, lang = asr_transcribe(audio_bytes, mime_type=req.mime_type, language=req.language)
    return TranscribeResponse(text=text, language_detected=lang)
```

- [ ] **Step 8: Write route-level integration test**

Append to `tests/test_asr.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.slow
def test_transcribe_route_end_to_end():
    client = TestClient(app)
    audio_b64 = base64.b64encode(FIXTURE.read_bytes()).decode()
    resp = client.post(
        "/transcribe",
        json={"audio_base64": audio_b64, "mime_type": "audio/wav", "language": "en"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "hello" in body["text"].lower()
    assert body["language_detected"] == "en"
```

- [ ] **Step 9: Run — expect PASS**

```bash
pytest tests/test_asr.py -v -m slow
```

Expected: 2 passed.

- [ ] **Step 10: Commit**

```bash
git add python-sidecar/
git commit -m "feat(sidecar): whisper ASR via faster-whisper

Adds app/asr.py wrapping faster-whisper (CPU, int8, base model).
Wires /transcribe route end-to-end. Fixture: espeak-generated
'hello world' WAV, ~100KB."
```

---

## Task 5 — Node `sidecar_client` with tests

**Files:**
- Create: `backend/lib/sidecar_client.js`
- Create: `backend/test/sidecar_client.test.js`
- Modify: `backend/package.json` (add test script + undici dep)

- [ ] **Step 1: Add undici and test script**

`backend/package.json`:

```json
{
  "name": "project-aid-backend",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "start": "node server.js",
    "test": "node --test test/"
  },
  "dependencies": {
    "axios": "^1.7.7",
    "cors": "^2.8.5",
    "dotenv": "^16.4.5",
    "express": "^4.21.0",
    "fluent-ffmpeg": "^2.1.3",
    "undici": "^6.19.8"
  }
}
```

(Merge with whatever is already in `backend/package.json`. Add `"type": "module"`; existing code uses `require`, Task 9 converts one module at a time.)

Run `npm install` in `backend/`.

- [ ] **Step 2: Write the failing sidecar-client test**

Create `backend/test/sidecar_client.test.js`:

```javascript
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
```

- [ ] **Step 3: Run — expect FAIL (no module)**

```bash
cd backend && npm test
```

Expected: failure on `import { SidecarClient } from '../lib/sidecar_client.js'`.

- [ ] **Step 4: Implement `backend/lib/sidecar_client.js`**

```javascript
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
```

- [ ] **Step 5: Run — expect PASS**

```bash
npm test
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/lib/sidecar_client.js backend/test/sidecar_client.test.js backend/package.json
git commit -m "feat(backend): typed Sidecar HTTP client with undici mock tests"
```

---

## Task 6 — `/transcribe` route on the Node backend (sidecar proxy)

**Files:**
- Create: `backend/routes/transcribe.js`
- Modify: `backend/server.js`
- Create: `backend/test/transcribe_route.test.js`

- [ ] **Step 1: Write a failing route test**

Create `backend/test/transcribe_route.test.js`:

```javascript
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
```

- [ ] **Step 2: Run — expect FAIL**

```bash
npm test
```

- [ ] **Step 3: Implement `backend/routes/transcribe.js`**

```javascript
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
```

- [ ] **Step 4: Wire it up in `server.js`**

Minimum diff in `backend/server.js`:

```javascript
import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

import { SidecarClient } from './lib/sidecar_client.js';
import { makeTranscribeRoute } from './routes/transcribe.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 8080;
const SIDECAR_URL = process.env.SIDECAR_URL || 'http://127.0.0.1:8090';

const app = express();
app.use(cors());
app.use(express.json({ limit: '25mb' }));
app.use(express.static(path.join(__dirname, '..')));

const tempDir = path.join(__dirname, '..', 'temp');
if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });

const sidecar = new SidecarClient(SIDECAR_URL);

app.use('/transcribe', makeTranscribeRoute(sidecar));

// (keep the existing /stitch handler for now — Task 11 will refactor it)

app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`));
```

Converting to ESM is a necessary part of this change because Task 5 pinned `"type": "module"`. The existing `/stitch` handler keeps working once you replace its `require` calls with equivalent `import` statements at the top of the file.

- [ ] **Step 5: Run — expect PASS**

```bash
npm test
```

Expected: route test passes.

- [ ] **Step 6: Manual smoke**

Start the sidecar, then the backend:

```bash
# terminal 1
cd python-sidecar && source .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8090

# terminal 2
cd backend && npm start
```

Send a test request (use the existing extension audio capture flow, or curl with a tiny b64 sample — any non-empty audio is fine; on failure we expect 502, on success the sidecar returns text).

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat(backend): add /transcribe route as sidecar proxy

Replaces the AssemblyAI block removed in Task 1. Converts server.js
to ESM so the new Sidecar client (undici-based) can be imported."
```

---

## Task 7 — Recon ISLRTC (document the site before scraping)

**Files:**
- Create: `scripts/recon_islrtc.py`
- Create: `scripts/recon_islrtc_report.md`
- Create: `docs/islrtc_licensing_email.md`

**Why a separate task:** scraping without first understanding the site structure leads to brittle code and rate-limit bans. One afternoon of reconnaissance saves days of rewriting.

- [ ] **Step 1: Write a probe script**

Create `scripts/recon_islrtc.py`:

```python
"""One-shot reconnaissance: probe ISLRTC dictionary URLs and log what we find.

Outputs findings to scripts/recon_islrtc_report.md. Manual review required.
"""

import json
from pathlib import Path
from urllib.parse import urljoin

import httpx

CANDIDATES = [
    "https://islrtc.nic.in/",
    "https://www.islrtc.nic.in/dictionary-0",
    "https://indiansignlanguage.org/dictionary/",
    "https://www.signlanguage.in/",
]

REPORT = Path(__file__).parent / "recon_islrtc_report.md"


def probe(url: str) -> dict:
    try:
        r = httpx.get(url, timeout=15, follow_redirects=True, headers={"User-Agent": "Project-AID recon"})
        return {
            "url": url,
            "final_url": str(r.url),
            "status": r.status_code,
            "content_type": r.headers.get("content-type", ""),
            "length": len(r.content),
            "title_snippet": r.text[:400].replace("\n", " ") if "text" in r.headers.get("content-type", "") else "",
        }
    except Exception as e:
        return {"url": url, "error": repr(e)}


def main():
    findings = [probe(u) for u in CANDIDATES]
    lines = ["# ISLRTC reconnaissance report\n"]
    lines.append("| URL | Final | Status | Type | Bytes |")
    lines.append("|---|---|---|---|---|")
    for f in findings:
        if "error" in f:
            lines.append(f"| {f['url']} | — | ERROR | {f['error']} | — |")
        else:
            lines.append(
                f"| {f['url']} | {f['final_url']} | {f['status']} | "
                f"{f['content_type']} | {f['length']} |"
            )
    lines.append("\n## Raw JSON\n\n```json\n" + json.dumps(findings, indent=2) + "\n```\n")
    lines.append(
        "\n## Manual review checklist\n"
        "- [ ] Is there a searchable dictionary page with per-word URLs?\n"
        "- [ ] Are videos hosted on the site or YouTube/other CDN?\n"
        "- [ ] Is there a robots.txt? What does it allow?\n"
        "- [ ] Is there a Terms page referencing redistribution?\n"
        "- [ ] Is the word list downloadable (CSV, JSON, XLS) directly?\n"
    )
    REPORT.write_text("\n".join(lines))
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it (from repo root)**

```bash
python scripts/recon_islrtc.py
```

Output: `scripts/recon_islrtc_report.md` with real status codes and snippets.

- [ ] **Step 3: Manually review `recon_islrtc_report.md`**

Walk the candidate URLs in a browser. Fill the checklist. Capture:
- The *real* dictionary URL pattern (e.g. `https://.../word/<slug>`)
- Video hosting (self-hosted MP4? YouTube? embed?)
- robots.txt contents
- Terms / copyright notice text

Commit the filled report.

- [ ] **Step 4: Draft the licensing email**

Create `docs/islrtc_licensing_email.md`:

```markdown
# Draft email to ISLRTC

**To:** ISLRTC@nic.in
**CC:** (developer's own)
**Subject:** Permission request — use of ISLRTC dictionary videos in an open-source accessibility tool

Dear ISLRTC team,

My name is [Yuvraj Singh] and I am building an open-source, non-commercial
Chrome extension that renders Indian Sign Language video alongside web
content (YouTube lectures, articles, educational platforms) to help ISL-signing
deaf users consume mainstream content and learn faster.

I would like to include the ISL sign videos from the ISLRTC dictionary as
the sign library, credited prominently to ISLRTC. The tool is free, source
code will be published under an open licence, and usage is educational /
accessibility-oriented.

Specifically I would like clarification on:

1. Can the dictionary videos be redistributed as part of an open-source tool?
2. If yes, under what attribution / licence terms?
3. If not, would ISLRTC permit users of the tool to stream the videos directly
   from the ISLRTC domain via their own browser (i.e. no redistribution, only
   linking / embedding)?
4. Is there an official dataset release or API that we should be using
   instead of scraping the dictionary pages?

I am happy to share the project plan, GitHub repo, and a short demo. I can
also discuss a formal MoU if helpful.

Thank you,
[Yuvraj Singh]
yuvraj.singh@kocharsoft.com
```

- [ ] **Step 5: Commit**

```bash
git add scripts/recon_islrtc.py scripts/recon_islrtc_report.md docs/islrtc_licensing_email.md
git commit -m "chore: ISLRTC site reconnaissance and licensing email draft"
```

Action item for user: send the email. Continue Task 8 regardless — scraping only public pages at polite rate is defensible under Indian fair-dealing (§52 of Copyright Act), and we can fall back to streaming-only if ISLRTC responds negatively.

---

## Task 8 — ISLRTC dictionary scraper

**Files:**
- Create: `scripts/scrape_islrtc.py`
- Create: `data/islrtc_raw.json` (generated, git-ignored)

**Important:** the exact selectors / URL pattern below are placeholders. Replace them with the real ones from `recon_islrtc_report.md` before running.

- [ ] **Step 1: Write the scraper skeleton**

Create `scripts/scrape_islrtc.py`:

```python
"""Scrape ISLRTC dictionary entries into data/islrtc_raw.json.

Respects robots.txt. Throttles to 1 req/sec. Resumable (skips already-fetched).

TODO before running: update DICTIONARY_INDEX_URL, ENTRY_URL_PATTERN, and the
three parse functions with the real selectors from recon_islrtc_report.md.
"""

import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

# ---- REPLACE AFTER RECON ----
DICTIONARY_INDEX_URL = "https://islrtc.nic.in/dictionary-0"  # TODO from recon
ENTRY_URL_PATTERN = re.compile(r"/dictionary/([a-z0-9-]+)$")  # TODO from recon
# -----------------------------

OUT = Path(__file__).parent.parent / "data" / "islrtc_raw.json"
OUT.parent.mkdir(parents=True, exist_ok=True)
THROTTLE_SEC = 1.0


def fetch(client: httpx.Client, url: str) -> str:
    r = client.get(url, timeout=30, follow_redirects=True)
    r.raise_for_status()
    return r.text


def list_entry_urls(client: httpx.Client) -> list[str]:
    """Return absolute URLs of all dictionary entries."""
    html = fetch(client, DICTIONARY_INDEX_URL)
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for a in soup.select("a[href]"):  # TODO refine selector after recon
        href = a["href"]
        if ENTRY_URL_PATTERN.search(href):
            urls.append(urljoin(DICTIONARY_INDEX_URL, href))
    return sorted(set(urls))


def parse_entry(html: str, entry_url: str) -> dict | None:
    """Parse a single dictionary entry page. Return None if video missing."""
    soup = BeautifulSoup(html, "html.parser")
    # TODO replace these selectors with real ones from recon.
    word_el = soup.select_one("h1")
    video_el = soup.select_one("video source, a[href$='.mp4']")
    if not word_el or not video_el:
        return None
    word = word_el.get_text(strip=True).lower()
    video_url = video_el.get("src") or video_el.get("href")
    return {
        "word": word,
        "slug": urlparse(entry_url).path.rsplit("/", 1)[-1],
        "entry_url": entry_url,
        "video_url": urljoin(entry_url, video_url) if video_url else None,
    }


def main():
    existing = json.loads(OUT.read_text()) if OUT.exists() else []
    seen = {e["entry_url"] for e in existing}

    with httpx.Client(headers={"User-Agent": "Project-AID scraper (contact: yuvraj.singh@kocharsoft.com)"}) as client:
        urls = list_entry_urls(client)
        print(f"found {len(urls)} entries; {len(urls) - len(seen)} new")

        for i, url in enumerate(urls):
            if url in seen:
                continue
            try:
                entry = parse_entry(fetch(client, url), url)
                if entry:
                    existing.append(entry)
                    if len(existing) % 50 == 0:
                        OUT.write_text(json.dumps(existing, indent=2))
                        print(f"[{i}/{len(urls)}] saved checkpoint with {len(existing)} entries")
            except Exception as e:
                print(f"[{i}/{len(urls)}] fail {url}: {e}")
            time.sleep(THROTTLE_SEC)

    OUT.write_text(json.dumps(existing, indent=2))
    print(f"done. {len(existing)} entries in {OUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Install deps (already-available venv OR top-level script deps)**

```bash
pip install httpx beautifulsoup4
```

(Add to a top-level `scripts/requirements.txt` if preferred.)

- [ ] **Step 3: Replace the TODOs using `recon_islrtc_report.md`**

This is manual. The three things to update:
1. `DICTIONARY_INDEX_URL`
2. `ENTRY_URL_PATTERN`
3. The two selectors in `parse_entry` (word element, video element)

- [ ] **Step 4: Dry-run on 10 entries**

Temporarily cap the loop to 10 entries, run, inspect `data/islrtc_raw.json`. If words and video URLs look correct, remove the cap and run fully.

- [ ] **Step 5: Full scrape (expect 20–40 minutes at 1 req/sec for ~10K entries)**

```bash
python scripts/scrape_islrtc.py
```

Resumable: re-run safely if interrupted.

- [ ] **Step 6: Add the raw file to `.gitignore`**

Append to `.gitignore`:

```
data/islrtc_raw.json
data/clip_cache/
```

- [ ] **Step 7: Commit**

```bash
git add scripts/scrape_islrtc.py .gitignore
git commit -m "feat(scripts): ISLRTC dictionary scraper (rate-limited, resumable)"
```

---

## Task 9 — Build `isl_wordmap.json`

**Files:**
- Create: `scripts/build_wordmap.py`
- Create: `data/isl_wordmap.json` (generated, committed)
- Modify: `manifest.json`

- [ ] **Step 1: Write build script**

Create `scripts/build_wordmap.py`:

```python
"""Convert data/islrtc_raw.json -> data/isl_wordmap.json.

Format (flat, matches extension expectation):
{
  "book":   { "clip_url": "https://...", "source": "islrtc" },
  "school": { "clip_url": "https://...", "source": "islrtc" }
}
"""

import json
from pathlib import Path

RAW = Path(__file__).parent.parent / "data" / "islrtc_raw.json"
OUT = Path(__file__).parent.parent / "data" / "isl_wordmap.json"


def normalize(word: str) -> str:
    return word.strip().lower()


def main():
    raw = json.loads(RAW.read_text())
    wm: dict[str, dict] = {}
    skipped = 0

    for entry in raw:
        if not entry.get("video_url"):
            skipped += 1
            continue
        key = normalize(entry["word"])
        if key in wm:
            continue  # first wins; ISLRTC entries occasionally duplicate
        wm[key] = {"clip_url": entry["video_url"], "source": "islrtc"}

    OUT.write_text(json.dumps(wm, indent=2, sort_keys=True))
    print(f"wrote {len(wm)} entries (skipped {skipped}) to {OUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run**

```bash
python scripts/build_wordmap.py
```

Expected: `wrote ~10000 entries to data/isl_wordmap.json`.

- [ ] **Step 3: Archive the old ASL wordmap**

```bash
mv data/wordmap.json data/wordmap_wlasl.archive.json
```

- [ ] **Step 4: Update `manifest.json` to expose the new file**

In `manifest.json`, update `web_accessible_resources`:

```json
  "web_accessible_resources": [
    {
      "resources": [
        "data/isl_wordmap.json"
      ],
      "matches": ["<all_urls>"]
    }
  ]
```

- [ ] **Step 5: Commit**

```bash
git add scripts/build_wordmap.py data/isl_wordmap.json data/wordmap_wlasl.archive.json data/wordmap.json manifest.json
git commit -m "feat(data): build ISL wordmap from ISLRTC scrape

Archives ASL wordmap. Exposes data/isl_wordmap.json to the extension."
```

---

## Task 10 — Streaming clip cache (Node)

**Files:**
- Create: `backend/lib/clip_cache.js`
- Create: `backend/test/clip_cache.test.js`

**Behaviour:** `get(clipId, clipUrl)` returns a local filesystem path. If the clip is cached, return path without network. If not, stream from `clipUrl`, write to `CLIP_CACHE_DIR/<sha1(clipId)>.mp4` atomically, return path.

- [ ] **Step 1: Write the failing test**

Create `backend/test/clip_cache.test.js`:

```javascript
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
```

- [ ] **Step 2: Run — expect FAIL**

```bash
npm test
```

- [ ] **Step 3: Implement `backend/lib/clip_cache.js`**

```javascript
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
```

- [ ] **Step 4: Run — expect PASS**

```bash
npm test
```

- [ ] **Step 5: Commit**

```bash
git add backend/lib/clip_cache.js backend/test/clip_cache.test.js
git commit -m "feat(backend): streaming clip cache with atomic writes"
```

---

## Task 11 — spaCy wrapper and `/parse` route

**Files:**
- Modify: `python-sidecar/pyproject.toml`
- Create: `python-sidecar/app/parse.py`
- Create: `python-sidecar/tests/test_parse.py`
- Modify: `python-sidecar/app/main.py`

- [ ] **Step 1: Add spaCy**

Add to `pyproject.toml`:

```toml
    "spacy==3.7.6",
```

Install and download model:

```bash
pip install -e ".[dev]"
python -m spacy download en_core_web_sm
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_parse.py`:

```python
import pytest

from app.parse import parse_clauses


def test_parse_returns_tokens_with_pos_and_lemma():
    [clause] = parse_clauses("The dogs ran home.", language="en")
    texts = [t.text for t in clause.tokens]
    assert "dogs" in texts
    ran = next(t for t in clause.tokens if t.text == "ran")
    assert ran.lemma == "run"
    assert ran.pos == "VERB"


def test_parse_splits_sentences_into_clauses():
    clauses = parse_clauses("I run. You walk.", language="en")
    assert len(clauses) == 2
    assert any(t.text == "run" for t in clauses[0].tokens)
    assert any(t.text == "walk" for t in clauses[1].tokens)


def test_parse_marks_stop_words():
    [clause] = parse_clauses("The cat is here.", language="en")
    stops = [t.text for t in clause.tokens if t.is_stop]
    assert "The" in stops or "the" in stops
    assert "is" in stops
```

- [ ] **Step 3: Run — expect FAIL**

```bash
pytest tests/test_parse.py -v
```

- [ ] **Step 4: Implement `app/parse.py`**

```python
"""spaCy-based clause parsing for English. Hindi added in Month 3."""

from functools import lru_cache

import spacy

from app.models import Language, ParsedClause, ParsedToken


@lru_cache(maxsize=1)
def _nlp():
    return spacy.load("en_core_web_sm")


def parse_clauses(text: str, language: Language = "en") -> list[ParsedClause]:
    if language != "en":
        raise NotImplementedError("Hindi parsing lands in Month 3")
    doc = _nlp()(text)
    clauses: list[ParsedClause] = []
    for sent in doc.sents:
        tokens = [
            ParsedToken(
                text=t.text,
                lemma=t.lemma_,
                pos=t.pos_,
                dep=t.dep_,
                head=t.head.i - sent.start,
                is_stop=bool(t.is_stop),
            )
            for t in sent
            if not t.is_punct
        ]
        clauses.append(ParsedClause(tokens=tokens, language="en"))
    return clauses
```

- [ ] **Step 5: Wire `/parse` in `app/main.py`**

```python
from app.parse import parse_clauses


@app.post("/parse", response_model=ParseResponse)
def parse(req: ParseRequest) -> ParseResponse:
    return ParseResponse(clauses=parse_clauses(req.text, req.language))
```

- [ ] **Step 6: Run — expect PASS**

```bash
pytest tests/test_parse.py -v
```

- [ ] **Step 7: Commit**

```bash
git add python-sidecar/
git commit -m "feat(sidecar): spaCy clause parser and /parse route"
```

---

## Task 12 — Rule engine scaffold + YAML loader

**Files:**
- Create: `python-sidecar/app/gloss.py`
- Create: `python-sidecar/app/rules.yaml`
- Create: `python-sidecar/tests/test_gloss.py`
- Modify: `python-sidecar/pyproject.toml` (add pyyaml)

- [ ] **Step 1: Add PyYAML**

In `pyproject.toml`:

```toml
    "pyyaml==6.0.2",
```

Install: `pip install -e ".[dev]"`.

- [ ] **Step 2: Define rule schema in YAML**

Create `app/rules.yaml`:

```yaml
# ISL gloss rules. Each rule has an id, a kind, and parameters.
# Kinds: drop_pos, lemmatize_verb, reorder_sov, hoist_time_first,
#        move_negation_after_verb, wh_to_end, normalize_pronoun,
#        plural_repetition, possessive_drop.
# Rules run in the order listed.
#
# Any change here is meant to be reviewable by a deaf advisor.

rules:
  - id: drop_determiners
    kind: drop_pos
    pos: [DET]

  - id: drop_aux
    kind: drop_pos
    pos: [AUX]

  - id: drop_adp_function_words
    kind: drop_lemma
    lemmas: [to, of, for, with, at]
    # NOTE with is semantically "BROTHER WITH" in ISL -> we keep "with"
    # as WITH sign. This rule excludes it. Remove once a deaf advisor
    # confirms preferred behaviour.

  - id: lemmatize_verbs
    kind: lemmatize_verb

  - id: normalize_pronouns
    kind: normalize_pronoun

  - id: reorder_sov
    kind: reorder_sov

  - id: hoist_time_first
    kind: hoist_time_first
    time_lemmas: [today, tomorrow, yesterday, now, later, morning, evening, night]

  - id: move_negation
    kind: move_negation_after_verb

  - id: wh_to_end
    kind: wh_to_end
    wh_lemmas: [who, what, where, when, why, how]

  - id: plural_marking
    kind: plural_repetition

  - id: drop_possessives
    kind: possessive_drop

  - id: number_pass_through
    kind: number_pass_through
```

(12 rules to start; we'll add the final 3 in Task 13 based on what shows up in testing.)

- [ ] **Step 3: Write the first failing gloss test**

Create `tests/test_gloss.py`:

```python
from app.gloss import to_gloss
from app.parse import parse_clauses


def gloss_of(text: str) -> list[str]:
    clause = parse_clauses(text, "en")[0]
    return [g.gloss for g in to_gloss(clause)]


def test_drops_articles_and_aux():
    assert gloss_of("The cat is here.") == ["CAT", "HERE"]


def test_lemmatizes_verbs():
    out = gloss_of("I am running.")
    assert "RUN" in out
    assert "running" not in [o.lower() for o in out]
```

- [ ] **Step 4: Run — expect FAIL**

```bash
pytest tests/test_gloss.py -v
```

- [ ] **Step 5: Implement `app/gloss.py` (scaffolding + first two rules)**

```python
"""Rule engine: parsed English clause -> ISL gloss token list."""

from pathlib import Path
from typing import Callable

import yaml

from app.models import GlossToken, ParsedClause, ParsedToken

RulesPath = Path(__file__).parent / "rules.yaml"


def _load_rules() -> list[dict]:
    return yaml.safe_load(RulesPath.read_text())["rules"]


# ---- Rule implementations ----

def _drop_pos(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    return [t for t in tokens if t.pos not in params["pos"]]


def _drop_lemma(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    return [t for t in tokens if t.lemma.lower() not in params["lemmas"]]


def _lemmatize_verb(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    out: list[ParsedToken] = []
    for t in tokens:
        if t.pos in ("VERB",):
            out.append(t.model_copy(update={"text": t.lemma}))
        else:
            out.append(t)
    return out


# More rule implementations land in Task 13.

RULES: dict[str, Callable[[list[ParsedToken], dict], list[ParsedToken]]] = {
    "drop_pos": _drop_pos,
    "drop_lemma": _drop_lemma,
    "lemmatize_verb": _lemmatize_verb,
}


def _apply_rules(tokens: list[ParsedToken]) -> list[ParsedToken]:
    for rule in _load_rules():
        impl = RULES.get(rule["kind"])
        if impl is None:
            continue  # filled in by later tasks
        tokens = impl(tokens, rule)
    return tokens


def to_gloss(clause: ParsedClause) -> list[GlossToken]:
    processed = _apply_rules(list(clause.tokens))
    return [
        GlossToken(gloss=t.text.upper(), kind="sign", source_text=t.text)
        for t in processed
    ]
```

- [ ] **Step 6: Run — expect PASS**

```bash
pytest tests/test_gloss.py -v
```

Expected: 2 passed.

- [ ] **Step 7: Commit**

```bash
git add python-sidecar/
git commit -m "feat(sidecar): YAML rule engine scaffold with drop+lemmatize rules"
```

---

## Task 13 — Implement the remaining 10 gloss rules

**Files:**
- Modify: `python-sidecar/app/gloss.py`
- Modify: `python-sidecar/tests/test_gloss.py`
- Create: `python-sidecar/tests/fixtures/en_isl_pairs.json`

**Approach:** one rule at a time, each with its own test, each followed by running the growing `en_isl_pairs.json` fixture.

- [ ] **Step 1: Add `normalize_pronoun` rule**

In `app/gloss.py`:

```python
PRONOUN_MAP = {
    "i": "I", "me": "I", "my": "I", "mine": "I",
    "you": "YOU", "your": "YOU", "yours": "YOU",
    "he": "HE-SHE", "she": "HE-SHE", "him": "HE-SHE", "her": "HE-SHE",
    "his": "HE-SHE", "hers": "HE-SHE",
    "we": "WE", "us": "WE", "our": "WE", "ours": "WE",
    "they": "THEY", "them": "THEY", "their": "THEY",
    "it": "IT",
}


def _normalize_pronoun(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    out: list[ParsedToken] = []
    for t in tokens:
        if t.pos == "PRON":
            mapped = PRONOUN_MAP.get(t.text.lower())
            if mapped:
                out.append(t.model_copy(update={"text": mapped}))
                continue
        out.append(t)
    return out


RULES["normalize_pronoun"] = _normalize_pronoun
```

Test it:

```python
def test_pronoun_normalization():
    assert "I" in gloss_of("I see the dog.")
    assert "YOU" in gloss_of("Your book is here.")
```

Run. Commit: `feat(sidecar): ISL pronoun normalization rule`.

- [ ] **Step 2: Add `reorder_sov` rule**

In `app/gloss.py`:

```python
def _reorder_sov(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    """If a clause has S V O (dep tags nsubj / dobj / ROOT verb), move O before V."""
    verb_idx = next((i for i, t in enumerate(tokens) if t.pos == "VERB"), None)
    if verb_idx is None:
        return tokens
    obj_idx = next(
        (i for i, t in enumerate(tokens) if t.dep in ("dobj", "obj", "attr") and i > verb_idx),
        None,
    )
    if obj_idx is None:
        return tokens
    reordered = tokens.copy()
    obj = reordered.pop(obj_idx)
    reordered.insert(verb_idx, obj)
    return reordered


RULES["reorder_sov"] = _reorder_sov
```

Test:

```python
def test_sov_reorder():
    # "I drink water" -> I WATER DRINK
    assert gloss_of("I drink water.") == ["I", "WATER", "DRINK"]
```

Run. Commit.

- [ ] **Step 3: Add `hoist_time_first` rule**

```python
def _hoist_time_first(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    time_lemmas = set(params["time_lemmas"])
    time_idx = next(
        (i for i, t in enumerate(tokens) if t.lemma.lower() in time_lemmas),
        None,
    )
    if time_idx is None or time_idx == 0:
        return tokens
    out = tokens.copy()
    t = out.pop(time_idx)
    return [t] + out


RULES["hoist_time_first"] = _hoist_time_first
```

Test:

```python
def test_time_hoist():
    # "I go to school tomorrow" -> TOMORROW I SCHOOL GO
    out = gloss_of("I go to school tomorrow.")
    assert out[0] == "TOMORROW"
```

Run. Commit.

- [ ] **Step 4: Add `move_negation_after_verb` rule**

```python
def _move_negation(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    neg_idx = next((i for i, t in enumerate(tokens) if t.dep == "neg" or t.text.lower() == "not"), None)
    if neg_idx is None:
        return tokens
    verb_idx = next((i for i, t in enumerate(tokens) if t.pos == "VERB"), None)
    if verb_idx is None or neg_idx > verb_idx:
        return tokens
    out = tokens.copy()
    neg = out.pop(neg_idx)
    if neg_idx < verb_idx:
        verb_idx -= 1
    out.insert(verb_idx + 1, neg)
    return out


RULES["move_negation_after_verb"] = _move_negation
```

Test:

```python
def test_negation_move():
    # "I do not go" -> I GO NOT
    out = gloss_of("I do not go.")
    assert out.index("GO") < out.index("NOT")
```

Run. Commit.

- [ ] **Step 5: Add `wh_to_end` rule**

```python
def _wh_to_end(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    wh = set(params["wh_lemmas"])
    idx = next((i for i, t in enumerate(tokens) if t.lemma.lower() in wh), None)
    if idx is None or idx == len(tokens) - 1:
        return tokens
    out = tokens.copy()
    t = out.pop(idx)
    out.append(t)
    return out


RULES["wh_to_end"] = _wh_to_end
```

Test:

```python
def test_wh_to_end():
    # "Where are you going?" -> YOU GO WHERE
    out = gloss_of("Where are you going?")
    assert out[-1] == "WHERE"
```

Run. Commit.

- [ ] **Step 6: Add `plural_repetition` rule**

```python
def _plural_repetition(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    out: list[ParsedToken] = []
    for t in tokens:
        if t.pos == "NOUN" and t.text.lower() != t.lemma.lower() and t.text.lower().endswith("s"):
            out.append(t.model_copy(update={"text": f"{t.lemma}+"}))
        else:
            out.append(t)
    return out


RULES["plural_repetition"] = _plural_repetition
```

Test:

```python
def test_plural_marking():
    out = gloss_of("The dogs run.")
    assert any(tok == "DOG+" for tok in out)
```

Run. Commit.

- [ ] **Step 7: Add `possessive_drop`**

```python
def _possessive_drop(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    return [t for t in tokens if t.dep != "poss" or t.text.lower() in ("i", "you", "we", "he", "she", "they")]


RULES["possessive_drop"] = _possessive_drop
```

Test:

```python
def test_possessive_juxtaposition():
    # "My book" -> I BOOK (my mapped to I by pronoun rule, then possessive_drop is a no-op here)
    out = gloss_of("My book is here.")
    assert out[0] == "I"
    assert "BOOK" in out
```

Run. Commit.

- [ ] **Step 8: Add `number_pass_through`**

```python
def _number_pass_through(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    # Placeholder: keep numerals as-is (ISL number signs exist in wordmap).
    return tokens


RULES["number_pass_through"] = _number_pass_through
```

(Trivial for now; later tasks map numerals to ISL number sign IDs.)

- [ ] **Step 9: Build the 50-pair gold fixture**

Create `tests/fixtures/en_isl_pairs.json`. Fifty hand-written English → ISL gloss pairs, chosen to exercise each rule at least twice. Start with these 10 and add the remaining 40 over the week with a deaf advisor reviewing:

```json
[
  {"en": "I drink water.",              "isl": ["I", "WATER", "DRINK"]},
  {"en": "The cat is here.",            "isl": ["CAT", "HERE"]},
  {"en": "I am running.",               "isl": ["I", "RUN"]},
  {"en": "I go to school tomorrow.",    "isl": ["TOMORROW", "I", "SCHOOL", "GO"]},
  {"en": "I do not go.",                "isl": ["I", "GO", "NOT"]},
  {"en": "Where are you going?",        "isl": ["YOU", "GO", "WHERE"]},
  {"en": "The dogs run.",               "isl": ["DOG+", "RUN"]},
  {"en": "My book is here.",            "isl": ["I", "BOOK", "HERE"]},
  {"en": "She reads the book.",         "isl": ["HE-SHE", "BOOK", "READ"]},
  {"en": "We go home yesterday.",       "isl": ["YESTERDAY", "WE", "HOME", "GO"]}
]
```

- [ ] **Step 10: Parametric test against the fixture**

Append to `tests/test_gloss.py`:

```python
import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "en_isl_pairs.json"


@pytest.mark.parametrize("pair", json.loads(FIXTURES.read_text()))
def test_gold_pair(pair):
    got = gloss_of(pair["en"])
    assert got == pair["isl"], f"{pair['en']!r}: got {got}, want {pair['isl']}"
```

Run. Expect initially some fails — which is fine: each failure is a real rule bug or a real pair bug. Either fix the rule or flag the pair for deaf-advisor review.

Target: at least 40/50 passing by end of Week 3. The remaining 10 become Week-4 tuning OR get moved to Month-2 post-MVP.

- [ ] **Step 11: Wire `/gloss` route**

In `app/main.py`:

```python
from app.gloss import to_gloss
from app.parse import parse_clauses


@app.post("/gloss", response_model=GlossResponse)
def gloss(req: GlossRequest) -> GlossResponse:
    clauses = parse_clauses(req.text, req.language)
    tokens: list[GlossToken] = []
    for c in clauses:
        tokens.extend(to_gloss(c))
    return GlossResponse(gloss=tokens)
```

Route-level test in `tests/test_routing.py`:

```python
def test_gloss_returns_tokens():
    resp = client.post("/gloss", json={"text": "I drink water.", "language": "en"})
    assert resp.status_code == 200
    body = resp.json()
    assert [t["gloss"] for t in body["gloss"]] == ["I", "WATER", "DRINK"]
```

Run. Commit.

---

## Task 14 — `/sign` end-to-end route on Node backend

**Files:**
- Create: `backend/routes/sign.js`
- Create: `backend/test/sign_route.test.js`
- Modify: `backend/server.js`

- [ ] **Step 1: Write the failing smoke test**

Create `backend/test/sign_route.test.js`:

```javascript
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

  // Fake clip HTTP server that returns a tiny valid MP4 for any path.
  clipServer = createServer((req, res) => {
    const mp4 = readFileSync(new URL('./fixtures/black_1s.mp4', import.meta.url));
    res.writeHead(200, { 'content-type': 'video/mp4' });
    res.end(mp4);
  });
  await new Promise((r) => clipServer.listen(0, r));
  clipBaseUrl = `http://127.0.0.1:${clipServer.address().port}`;

  // Minimal wordmap covering the test sentence.
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
```

Prepare fixture `backend/test/fixtures/black_1s.mp4`: a 1-second black MP4 at 640x480@25fps. Generate once:

```bash
ffmpeg -f lavfi -i color=c=black:s=640x480:d=1 -r 25 -c:v libx264 -pix_fmt yuv420p backend/test/fixtures/black_1s.mp4
```

- [ ] **Step 2: Run — expect FAIL**

```bash
npm test
```

- [ ] **Step 3: Implement `backend/routes/sign.js`**

```javascript
import { Router } from 'express';
import { readFileSync, existsSync, unlinkSync, writeFileSync } from 'node:fs';
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

      // Write concat list file
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
```

Note: this assumes all clips are already normalized to the same resolution/framerate. For the test the fixture guarantees this. For production clips we will normalize in Month 2. Keep Month 1 simple: stitch-as-is.

- [ ] **Step 4: Mount in `server.js`**

```javascript
import { makeSignRoute } from './routes/sign.js';
import { ClipCache } from './lib/clip_cache.js';

const CLIP_CACHE_DIR = process.env.CLIP_CACHE_DIR || path.join(__dirname, '..', 'data', 'clip_cache');
const WORDMAP_PATH = path.join(__dirname, '..', 'data', 'isl_wordmap.json');

app.use('/sign', makeSignRoute({
  sidecar,
  clipCache: new ClipCache(CLIP_CACHE_DIR),
  wordmapPath: WORDMAP_PATH,
}));
```

- [ ] **Step 5: Run — expect PASS**

```bash
npm test
```

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat(backend): /sign end-to-end route (text -> ISL MP4)

Orchestrates gloss from sidecar, clip fetch from cache, FFmpeg
concat. Assumes normalized clips; normalisation lands in Month 2."
```

---

## Task 15 — Wire popup to `/sign` and do a real smoke test

**Files:**
- Modify: `popup/popup.html`
- Modify: `popup/popup.js`

- [ ] **Step 1: Read the existing popup**

Open `popup/popup.html` and `popup/popup.js` and understand the current flow (text input, "generate" button, video preview).

- [ ] **Step 2: Add a text area + "Sign it" button**

Minimum change in `popup/popup.html`: ensure there is a `<textarea id="signInput">` and a `<button id="signBtn">Sign it</button>` and a `<video id="signPreview" controls></video>`.

- [ ] **Step 3: Wire the button to `/sign`**

In `popup/popup.js`, add:

```javascript
const SIGN_ENDPOINT = 'http://127.0.0.1:8080/sign';

document.getElementById('signBtn').addEventListener('click', async () => {
  const text = document.getElementById('signInput').value.trim();
  if (!text) return;

  const resp = await fetch(SIGN_ENDPOINT, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ text }),
  });

  if (!resp.ok) {
    alert(`Sign failed: ${resp.status}`);
    return;
  }

  const blob = await resp.blob();
  const video = document.getElementById('signPreview');
  video.src = URL.createObjectURL(blob);
  video.load();
});
```

- [ ] **Step 4: Manual end-to-end smoke**

1. Start sidecar: `cd python-sidecar && source .venv/bin/activate && uvicorn app.main:app --port 8090`
2. Start backend: `cd backend && npm start`
3. Load unpacked extension.
4. Open popup, paste: `I drink water.`, click Sign it. Expect a short MP4 playing back concatenated ISL clips.

- [ ] **Step 5: Commit**

```bash
git add popup/
git commit -m "feat(popup): wire Sign it button to /sign end-to-end"
```

---

## Task 16 — Recruit testers and run kickoff

**Files:**
- Create: `docs/tester_kickoff.md`

- [ ] **Step 1: Write kickoff doc**

Create `docs/tester_kickoff.md`:

```markdown
# Project-AID tester kickoff

## What we're building (one sentence)
A free Chrome extension that renders Indian Sign Language alongside web video
and text, so ISL-signing deaf users can consume mainstream content (YouTube,
lectures, articles) more easily.

## What we need from you (30 min / week, 4 months)
1. Use the tool on real content weekly.
2. Flag wrong/missing/awkward signs via the in-app flag button.
3. Join a 20-minute video call every 2 weeks for feedback.

## What this is NOT (honesty is part of the product)
- Not a replacement for a human interpreter.
- Not full ISL with facial grammar yet — starts closer to signed English in SOV order.
- Missing signs are fingerspelled; grammar will feel rough early.
- We will fix things you flag, in the open, with you named as a contributor
  if you opt in.

## Recruitment outreach template
Subject: Help build a free ISL tool for deaf students — 30 min/week

Hi [name],

I'm building an open-source Chrome extension that turns YouTube lectures and
web articles into ISL video for deaf users. I'm looking for 5–10 ISL signers
willing to test weekly and tell me what's wrong so I can fix it.

Commitment: ~30 min/week for 4 months, one 20-min call every 2 weeks.
No tech skills needed beyond using Chrome. You'll be credited (if you want) in
the public release.

Would you be open to a 15-min intro call this week?

— [Yuvraj]

## Week 0 kickoff call agenda (60 min)
1. Who everyone is — signers and developer (10)
2. Demo of the current MVP (sign "I drink water") (10)
3. Honest limitations walkthrough (10)
4. Feedback tooling — how to flag (10)
5. Testing cadence + expectations (10)
6. Q&A (10)
```

- [ ] **Step 2: Send outreach (manual)**

Use the template above. Target: confirm 5–10 committed testers by end of Week 4.

- [ ] **Step 3: Commit**

```bash
git add docs/tester_kickoff.md
git commit -m "docs: tester recruitment and kickoff"
```

---

## Month 1 exit checklist (run this before saying "done")

- [ ] AssemblyAI key rotated on provider side; `server.js` contains no secrets
- [ ] Python sidecar starts cleanly: `uvicorn app.main:app --port 8090` → `/health` returns 200
- [ ] `pytest -v` in `python-sidecar/` passes (routing, parse, gloss, ASR slow test)
- [ ] `npm test` in `backend/` passes (sidecar_client, transcribe_route, clip_cache, sign_route)
- [ ] `python scripts/recon_islrtc.py` run and report committed
- [ ] ISLRTC licensing email sent
- [ ] `data/isl_wordmap.json` committed with ≥5000 entries
- [ ] Extension popup: paste "I drink water." → ISL video plays back
- [ ] Extension popup: paste "I go to school tomorrow." → TOMORROW I SCHOOL GO
- [ ] ≥40 / 50 gold pairs passing
- [ ] 5–10 deaf testers confirmed; kickoff call scheduled
- [ ] `docs/tester_kickoff.md` and `docs/islrtc_licensing_email.md` committed

---

## Next plan

When this one is complete, write `docs/superpowers/plans/2026-05-14-month-2-core-product.md` covering:
- ISL two-handed fingerspelling clip library (record with a deaf collaborator)
- OOV resolver (paraphrase map, fingerspelling fallback)
- Pre-processed YouTube flow (content script button + side panel signer + playhead sync)
- Feedback UI (flag buttons + local log + opt-in upload)
- First alpha ship to testers, weekly feedback loop
