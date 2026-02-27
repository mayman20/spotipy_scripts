from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import Settings


STATE_SALT = "spotify-auth-state"
SESSION_SALT = "spotify-session-token"


def get_serializer(settings: Settings) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.app_secret_key)


def make_state(settings: Settings, payload: dict) -> str:
    return get_serializer(settings).dumps(payload, salt=STATE_SALT)


def read_state(settings: Settings, token: str, max_age_seconds: int = 600) -> dict | None:
    try:
        return get_serializer(settings).loads(token, salt=STATE_SALT, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None


def make_session_token(settings: Settings, spotify_user_id: str) -> str:
    return get_serializer(settings).dumps({"spotify_user_id": spotify_user_id}, salt=SESSION_SALT)


def read_session_token(settings: Settings, token: str, max_age_seconds: int = 60 * 60 * 24 * 14) -> str | None:
    try:
        payload = get_serializer(settings).loads(token, salt=SESSION_SALT, max_age=max_age_seconds)
        return str(payload.get("spotify_user_id", "")).strip() or None
    except (BadSignature, SignatureExpired):
        return None
