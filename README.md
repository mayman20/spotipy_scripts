# spotipy_scripts

Spotify automation workspace for playlist management, listening-history workflows, and browser-based script execution.

## What This Project Shows

- API integrations with Spotify through Spotipy
- Backend and frontend coordination for authenticated user workflows
- Automation tooling that moved from local scripts toward a web product
- Deployment patterns using a static frontend plus hosted API backend

## Main Capabilities

- Mirror liked songs into target playlists
- Run vaulted playlist sync workflows
- Manage Spotify auth and token handling
- Trigger automation from a web interface instead of only local scripts
- Support analytics-style views such as dashboard summaries and listening insights

## Repo Layout

```txt
backend/                             FastAPI backend, auth, DB, task orchestration
website/spotify-script-hub-main/     React and TypeScript frontend
scripts/                             Local and legacy Spotify scripts
scripts/vaulted_add/                 Vaulted playlist sync workflow
scripts/liked_add/                   Liked songs mirror workflow
scripts/monthly_recommend/           Recommendation tooling
scripts/auth_tools/                  Spotify auth helpers
.github/workflows/                   Pages deploy and script-run workflows
```

## Architecture

1. User authenticates with Spotify.
2. Backend stores encrypted Spotify tokens.
3. Frontend calls backend endpoints to run or inspect workflows.
4. Backend executes playlist tasks and returns run results to the UI.

## Tech Stack

- Backend: FastAPI, Uvicorn, Spotipy, PostgreSQL, `httpx`
- Frontend: React, TypeScript, Vite
- Auth and security: Spotify OAuth, encrypted token storage
- Deployment: GitHub Pages for frontend, Render-style hosted backend

## Run The Script Shortcuts

From repo root:

```powershell
./vaulted.ps1
./liked.ps1
```

Batch equivalents:

```powershell
./vaulted.bat
./liked.bat
```

## Environment

Create `.env` at the project root with:

```bash
SPOTIPY_CLIENT_ID=...
SPOTIPY_CLIENT_SECRET=...
SPOTIPY_REDIRECT_URI=...
```

For the backend you also need:

```bash
DATABASE_URL=...
APP_SECRET_KEY=...
FRONTEND_URL=...
```

## Local Development

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Important backend env vars:

- `SPOTIPY_CLIENT_ID`
- `SPOTIPY_CLIENT_SECRET`
- `SPOTIPY_REDIRECT_URI`
- `DATABASE_URL`
- `APP_SECRET_KEY`
- `FRONTEND_URL`

### Frontend

From `website/spotify-script-hub-main`:

```bash
npm install
npm run dev
```

Create `.env.local` with:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Deployment Notes

- Frontend is suitable for GitHub Pages deployment.
- Backend can run on Render or a similar Python host.
- Tokens stored in the database are encrypted using a key derived from `APP_SECRET_KEY`.

## Current Caveats

- Some legacy script paths still exist alongside the newer web workflow.
- `Auto-remove from source` is a planned feature in the vaulted flow UI and is not fully enforced by backend execution yet.
