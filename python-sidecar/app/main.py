import base64

from fastapi import FastAPI, HTTPException

from app.asr import transcribe as asr_transcribe
from app.parse import parse_clauses
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
    audio_bytes = base64.b64decode(req.audio_base64)
    text, lang = asr_transcribe(audio_bytes, mime_type=req.mime_type, language=req.language)
    return TranscribeResponse(text=text, language_detected=lang)


@app.post("/parse", response_model=ParseResponse)
def parse(req: ParseRequest) -> ParseResponse:
    return ParseResponse(clauses=parse_clauses(req.text, req.language))


@app.post("/gloss", response_model=GlossResponse)
def gloss(req: GlossRequest) -> GlossResponse:
    raise HTTPException(status_code=501, detail="not implemented yet")
