import os


class Settings:
    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str
    database_url: str
    app_secret_key: str
    frontend_url: str

    def __init__(self) -> None:
        self.spotify_client_id = os.getenv("SPOTIPY_CLIENT_ID", "").strip()
        self.spotify_client_secret = os.getenv("SPOTIPY_CLIENT_SECRET", "").strip()
        self.spotify_redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "").strip()
        self.database_url = os.getenv("DATABASE_URL", "").strip()
        self.app_secret_key = os.getenv("APP_SECRET_KEY", "").strip()
        self.frontend_url = os.getenv("FRONTEND_URL", "").strip()

    def validate(self) -> None:
        missing = []
        if not self.spotify_client_id:
            missing.append("SPOTIPY_CLIENT_ID")
        if not self.spotify_client_secret:
            missing.append("SPOTIPY_CLIENT_SECRET")
        if not self.spotify_redirect_uri:
            missing.append("SPOTIPY_REDIRECT_URI")
        if not self.database_url:
            missing.append("DATABASE_URL")
        if not self.app_secret_key:
            missing.append("APP_SECRET_KEY")
        if not self.frontend_url:
            missing.append("FRONTEND_URL")
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
