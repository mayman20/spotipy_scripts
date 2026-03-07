import sqlite3
from base64 import urlsafe_b64encode
from datetime import datetime, timezone
from hashlib import sha256

import psycopg
from cryptography.fernet import Fernet, InvalidToken

from .config import Settings


def _use_sqlite(settings: Settings) -> bool:
    url = settings.database_url
    return not url or url.startswith("sqlite")


def _sqlite_path(settings: Settings) -> str:
    url = settings.database_url
    return url.replace("sqlite:///", "").replace("sqlite://", "") or "local_dev.db"


def _cipher(settings: Settings) -> Fernet:
    # Deterministic Fernet key derived from APP_SECRET_KEY so no extra env var is required.
    key_material = sha256(settings.app_secret_key.encode("utf-8")).digest()
    return Fernet(urlsafe_b64encode(key_material))


def _encrypt_token(settings: Settings, token: str) -> str:
    if not token:
        return token
    if token.startswith("enc::"):
        return token
    enc = _cipher(settings).encrypt(token.encode("utf-8")).decode("utf-8")
    return f"enc::{enc}"


def _decrypt_token(settings: Settings, token: str) -> str:
    if not token:
        return token
    if not token.startswith("enc::"):
        # Backward compatibility with older plaintext rows.
        return token
    payload = token[5:]
    try:
        return _cipher(settings).decrypt(payload.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        # If APP_SECRET_KEY changed, fail closed by returning empty string.
        return ""


def init_db(settings: Settings) -> None:
    if _use_sqlite(settings):
        with sqlite3.connect(_sqlite_path(settings)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS spotify_user_tokens (
                    spotify_user_id TEXT PRIMARY KEY,
                    display_name TEXT,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
    else:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS spotify_user_tokens (
                        spotify_user_id TEXT PRIMARY KEY,
                        display_name TEXT,
                        access_token TEXT NOT NULL,
                        refresh_token TEXT NOT NULL,
                        expires_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                conn.commit()


def upsert_tokens(
    settings: Settings,
    spotify_user_id: str,
    display_name: str,
    access_token: str,
    refresh_token: str,
    expires_at: datetime,
) -> None:
    access_token_enc = _encrypt_token(settings, access_token)
    refresh_token_enc = _encrypt_token(settings, refresh_token)

    if _use_sqlite(settings):
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(_sqlite_path(settings)) as conn:
            conn.execute(
                """
                INSERT INTO spotify_user_tokens
                    (spotify_user_id, display_name, access_token, refresh_token, expires_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(spotify_user_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    access_token = excluded.access_token,
                    refresh_token = excluded.refresh_token,
                    expires_at = excluded.expires_at,
                    updated_at = excluded.updated_at
                """,
                (spotify_user_id, display_name, access_token_enc, refresh_token_enc, expires_at.isoformat(), now),
            )
    else:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO spotify_user_tokens
                        (spotify_user_id, display_name, access_token, refresh_token, expires_at, updated_at)
                    VALUES
                        (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (spotify_user_id) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        access_token = EXCLUDED.access_token,
                        refresh_token = EXCLUDED.refresh_token,
                        expires_at = EXCLUDED.expires_at,
                        updated_at = NOW()
                    """,
                    (spotify_user_id, display_name, access_token_enc, refresh_token_enc, expires_at),
                )
                conn.commit()


def get_tokens(settings: Settings, spotify_user_id: str) -> dict | None:
    if _use_sqlite(settings):
        with sqlite3.connect(_sqlite_path(settings)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT spotify_user_id, display_name, access_token, refresh_token, expires_at"
                " FROM spotify_user_tokens WHERE spotify_user_id = ?",
                (spotify_user_id,),
            ).fetchone()
            if not row:
                return None
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            return {
                "spotify_user_id": row["spotify_user_id"],
                "display_name": row["display_name"] or "",
                "access_token": _decrypt_token(settings, row["access_token"]),
                "refresh_token": _decrypt_token(settings, row["refresh_token"]),
                "expires_at": expires_at,
            }
    else:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT spotify_user_id, display_name, access_token, refresh_token, expires_at"
                    " FROM spotify_user_tokens WHERE spotify_user_id = %s",
                    (spotify_user_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "spotify_user_id": row[0],
                    "display_name": row[1] or "",
                    "access_token": _decrypt_token(settings, row[2]),
                    "refresh_token": _decrypt_token(settings, row[3]),
                    "expires_at": row[4],
                }


def delete_tokens(settings: Settings, spotify_user_id: str) -> None:
    if _use_sqlite(settings):
        with sqlite3.connect(_sqlite_path(settings)) as conn:
            conn.execute(
                "DELETE FROM spotify_user_tokens WHERE spotify_user_id = ?",
                (spotify_user_id,),
            )
    else:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM spotify_user_tokens WHERE spotify_user_id = %s",
                    (spotify_user_id,),
                )
                conn.commit()


def is_expired(expires_at: datetime) -> bool:
    return expires_at <= datetime.now(timezone.utc)
