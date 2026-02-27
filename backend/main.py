from fastapi import FastAPI

app = FastAPI(title="Spotipy Scripts API", version="0.1.0")


@app.get("/")
def root() -> dict:
    return {"ok": True, "service": "spotipy_scripts_backend"}


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
