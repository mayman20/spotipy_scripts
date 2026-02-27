# Spotipy Scripts Workspace

This repository is organized as a Spotify-only project.

## Layout

- `website/` extracted website project
- `scripts/`
- `scripts/vaulted_add/` vaulted playlist sync script + data/output/cache/logs
- `scripts/liked_add/` liked songs mirror script + data/output/cache/logs
- `scripts/monthly_recommend/` monthly recommendation script and assets
- `scripts/auth_tools/get-spotify-refresh-token-main/` Spotify auth helper
- `.cache/` root OAuth cache files
- `.env` Spotify credentials file
- `_backup_YYYYMMDD_HHMM/` moved legacy/non-Spotify items and incoming zips

## Run

From project root:

- `./vaulted.bat`
- `./liked.bat`

PowerShell alternatives:

- `./vaulted.ps1`
- `./liked.ps1`

## Environment

Create/update `.env` at project root with Spotipy credentials:

- `SPOTIPY_CLIENT_ID`
- `SPOTIPY_CLIENT_SECRET`
- `SPOTIPY_REDIRECT_URI`

## Website

The extracted website project is in `website/`.

## GitHub Pages + Web Trigger

- GitHub Pages deploy workflow: `.github/workflows/deploy-pages.yml`
- Script run workflow: `.github/workflows/run-spotify-script.yml`
- Legacy workflow route is still available, but user-facing execution now runs through backend OAuth.

## Backend (Render)

- Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/healthz`
- Required env vars:
- `SPOTIPY_CLIENT_ID`
- `SPOTIPY_CLIENT_SECRET`
- `SPOTIPY_REDIRECT_URI` (Render callback URL)
- `DATABASE_URL`
- `APP_SECRET_KEY`
- `FRONTEND_URL` (GitHub Pages URL)

Frontend build env:

- `VITE_API_BASE_URL=https://<your-render-service>.onrender.com`
