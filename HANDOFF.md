# spotipy_scripts — handoff

Spotify scripts + `music-visualizer/`. Runs locally.

## Gitignored auth (NOT in git — staged on tree)
```
# from the repo root:
scp -i ~/.ssh/lightsail_tree.pem ubuntu@54.216.74.8:/home/ubuntu/repo-secrets/spotipy_scripts/.env .
scp -i ~/.ssh/lightsail_tree.pem ubuntu@54.216.74.8:/home/ubuntu/repo-secrets/spotipy_scripts/.spotify_cache music-visualizer/.spotify_cache
```
- `.env` — `SPOTIPY_CLIENT_ID` / `SPOTIPY_CLIENT_SECRET` / `SPOTIPY_REDIRECT_URI` + run config → place at repo ROOT. Required (every script + `backend/config.py` read it). Secret rotated 2026-05-28.
- `.spotify_cache` — Spotify OAuth token cache → place in `music-visualizer/`. If expired, the app re-auths via browser on first run (so this is convenience, not strictly required).

_Generated 2026-05-27 during repo-sync cleanup. Secrets on tree (54.216.74.8) under `/home/ubuntu/repo-secrets/`._
