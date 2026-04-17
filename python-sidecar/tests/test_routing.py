from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# /transcribe is covered by test_asr.py::test_transcribe_route_end_to_end
# (which sends real audio). The old "!= 404" stub was redundant once a real
# handler landed and would spuriously flow empty bytes into ASR.


def test_parse_route_exists():
    resp = client.post("/parse", json={"text": "hello", "language": "en"})
    assert resp.status_code != 404


def test_gloss_route_exists():
    resp = client.post("/gloss", json={"text": "hello", "language": "en"})
    assert resp.status_code != 404
