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
