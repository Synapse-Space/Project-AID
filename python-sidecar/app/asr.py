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
