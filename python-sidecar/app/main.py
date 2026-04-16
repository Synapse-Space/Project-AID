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
