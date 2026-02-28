from urllib.parse import quote_plus, urlparse

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .config import Settings
from .db import delete_tokens, get_tokens, init_db
from .security import make_session_token, make_state, read_session_token, read_state
from .spotify_auth import build_authorize_url, exchange_code_for_tokens, get_spotify_client_for_user, store_login_tokens
from .tasks import run_liked_add, run_vaulted_add

settings = Settings()
app = FastAPI(title="Spotipy Scripts API", version="0.2.0")

def _frontend_origins(frontend_url: str) -> list[str]:
    if not frontend_url:
        return ["*"]

    candidates = {frontend_url.rstrip("/")}
    parsed = urlparse(frontend_url)
    if parsed.scheme and parsed.netloc:
        candidates.add(f"{parsed.scheme}://{parsed.netloc}")
    return sorted(candidates)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins(settings.frontend_url),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    settings.validate()
    init_db(settings)


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header.")
    token = parts[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    return token


def _current_user_id(authorization: str | None) -> str:
    token = _extract_bearer_token(authorization)
    user_id = read_session_token(settings, token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")
    return user_id


@app.get("/")
def root() -> dict:
    return {"ok": True, "service": "spotipy_scripts_backend"}


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/auth/login")
def auth_login() -> RedirectResponse:
    state = make_state(settings, {"origin": settings.frontend_url})
    return RedirectResponse(build_authorize_url(settings, state), status_code=302)


@app.get("/auth/callback")
def auth_callback(code: str | None = None, state: str | None = None, error: str | None = None) -> RedirectResponse:
    if error:
        target = f"{settings.frontend_url}?login_error={quote_plus(error)}"
        return RedirectResponse(target, status_code=302)
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state.")

    payload = read_state(settings, state)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")

    token_data = exchange_code_for_tokens(settings, code)
    user = store_login_tokens(settings, token_data)
    session_token = make_session_token(settings, user["spotify_user_id"])

    target = (
        f"{settings.frontend_url}"
        f"?session_token={quote_plus(session_token)}"
        f"&spotify_user_id={quote_plus(user['spotify_user_id'])}"
    )
    return RedirectResponse(target, status_code=302)


@app.get("/me")
def me(authorization: str | None = Header(default=None, alias="Authorization")) -> dict:
    spotify_user_id = _current_user_id(authorization)
    row = get_tokens(settings, spotify_user_id)
    if not row:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"spotify_user_id": row["spotify_user_id"], "display_name": row["display_name"]}


@app.post("/run/vaulted")
def run_vaulted(authorization: str | None = Header(default=None, alias="Authorization")) -> dict:
    spotify_user_id = _current_user_id(authorization)
    sp, _ = get_spotify_client_for_user(settings, spotify_user_id)
    result = run_vaulted_add(sp)
    return {"ok": True, "script": "vaulted_add", "result": result}


@app.post("/run/liked")
def run_liked(authorization: str | None = Header(default=None, alias="Authorization")) -> dict:
    spotify_user_id = _current_user_id(authorization)
    sp, _ = get_spotify_client_for_user(settings, spotify_user_id)
    result = run_liked_add(sp)
    return {"ok": True, "script": "liked_add", "result": result}


@app.post("/logout")
def logout(authorization: str | None = Header(default=None, alias="Authorization")) -> dict:
    spotify_user_id = _current_user_id(authorization)
    delete_tokens(settings, spotify_user_id)
    return {"ok": True}
