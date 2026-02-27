from datetime import datetime, timezone

import psycopg

from .config import Settings


def get_conn(settings: Settings) -> psycopg.Connection:
    return psycopg.connect(settings.database_url)


def init_db(settings: Settings) -> None:
    with get_conn(settings) as conn:
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
    with get_conn(settings) as conn:
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
                (spotify_user_id, display_name, access_token, refresh_token, expires_at),
            )
            conn.commit()


def get_tokens(settings: Settings, spotify_user_id: str) -> dict | None:
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT spotify_user_id, display_name, access_token, refresh_token, expires_at
                FROM spotify_user_tokens
                WHERE spotify_user_id = %s
                """,
                (spotify_user_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "spotify_user_id": row[0],
                "display_name": row[1] or "",
                "access_token": row[2],
                "refresh_token": row[3],
                "expires_at": row[4],
            }


def delete_tokens(settings: Settings, spotify_user_id: str) -> None:
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM spotify_user_tokens WHERE spotify_user_id = %s", (spotify_user_id,))
            conn.commit()


def is_expired(expires_at: datetime) -> bool:
    return expires_at <= datetime.now(timezone.utc)
