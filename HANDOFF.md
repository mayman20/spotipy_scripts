# spotipy_scripts — handoff

Spotify scripts + `music-visualizer/`. Runs locally.

## Gitignored auth (NOT in git — staged on tree)
```
scp -i ~/.ssh/lightsail_tree.pem ubuntu@54.216.74.8:/home/ubuntu/repo-secrets/spotipy_scripts/.spotify_cache music-visualizer/.spotify_cache
```
- `.spotify_cache` — Spotify OAuth token cache → place in `music-visualizer/`. If expired, the app re-auths via browser on first run (so this is convenience, not strictly required).

_Generated 2026-05-27 during repo-sync cleanup. Secrets on tree (54.216.74.8) under `/home/ubuntu/repo-secrets/`._
