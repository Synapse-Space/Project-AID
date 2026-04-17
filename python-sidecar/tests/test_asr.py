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
