from fastapi import FastAPI

app = FastAPI(title="project-aid-sidecar", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
