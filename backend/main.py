from urllib.parse import quote_plus, urlparse

from fastapi import FastAPI, Header, HTTPException, Request
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
    # Local rapid-dev origins for Vite previews.
    candidates.update(
        {
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:8080",
            "http://localhost:8080",
        }
    )
    return sorted(candidates)


def _is_allowed_return_url(return_to: str) -> bool:
    try:
        parsed = urlparse(return_to)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False
        normalized_origin = f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return False
    if normalized_origin in _frontend_origins(settings.frontend_url):
        return True

    # Local dev: allow localhost/127.0.0.1 on any port.
    host = parsed.hostname or ""
    if host in {"127.0.0.1", "localhost"}:
        return True

    return False

app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins(settings.frontend_url),
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
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
def auth_login(request: Request, return_to: str | None = None) -> RedirectResponse:
    resolved_return_to = settings.frontend_url
    if return_to and _is_allowed_return_url(return_to):
        resolved_return_to = return_to
    else:
        referer = request.headers.get("referer", "")
        if referer and _is_allowed_return_url(referer):
            resolved_return_to = referer
    state = make_state(settings, {"return_to": resolved_return_to})
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

    return_to = str(payload.get("return_to") or settings.frontend_url)
    if not _is_allowed_return_url(return_to):
        return_to = settings.frontend_url

    target = (
        f"{return_to}"
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
