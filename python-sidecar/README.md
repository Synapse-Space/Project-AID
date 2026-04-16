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
