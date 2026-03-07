# Roadmap

## Milestones

1. Milestone 1: Cleanup + restructure + runners
- Create timestamped backup
- Move non-Spotify items to backup
- Rebuild project layout and runner scripts

2. Milestone 2: Confirm vaulted_add and liked_add run from new locations
- Run import/smoke checks
- Verify OAuth cache paths and `.env` loading

3. Milestone 3: Confirm monthly_recommend runs
- Validate script import and runtime path assumptions

4. Milestone 4: Website extracted and opens locally
- Verify `website/**/index.html` exists
- Start local dev server when needed

5. Milestone 5: Integrate scripts into website (future)
- Define API/automation bridge between website and Python scripts

## Daily Log

### 2026-02-27
- Reorganized repository into Spotify-focused structure
- Backed up non-Spotify files/folders and source website zip
- Added root runners, `.gitignore`, and project documentation
- Standardized `.env` and centralized cache files under `.cache/`

### 2026-02-28
- Deployed backend + frontend flow with Spotify OAuth login, Render API, and GitHub Pages UI
- Added dashboard metrics, time-range switching, top artists/tracks cards, and show-more (up to 25)
- Added playlist targeting rules for `liked_add` and `vaulted_add`:
- Rule order: automation tag match -> case-insensitive name match -> create new
- Added automatic tag append behavior for managed playlists without removing existing descriptions
- Added genre-based playlist recommendation section and Spotify open links in UI
- Added backend caching and split stats endpoints (`/stats/overview`, `/stats/top`) for faster loads

### 2026-03-07 (Sync Audit)
- Verified live backend route availability on Render:
  - `/stats/overview` -> 401 (route exists)
  - `/stats/top` -> 401 (route exists)
  - `/recommendations/genre-playlists` -> 401 (route exists)
  - `/automation/targets` -> 401 (route exists)
- Verified latest successful GitHub Pages deploy currently points to commit `5b70ff2`.
- Confirmed additional local, uncommitted backend/frontend changes exist and must be pushed for live site parity.
- Action taken: completed full local->main sync in commit `22b903e`.
- GitHub Pages deploy for `22b903e` completed successfully (workflow run `22801166898`).
- Live frontend bundle check confirmed latest features are present (includes `Mood Timeline` UI text).
- Render backend is not fully synced yet (new routes still 404):
  - `/stats/recently-played`
  - `/search/artists`
  - `/stats/artist-catalog`
  - `/stats/genre-breakdown`
  - `/stats/mood-timeline`
- Required next action: trigger/restart Render web service deploy from latest `main`.

## Recently Completed (2026-02-28 session 2)

- Fixed `added_7d` / `added_30d` counters (dead-code bug in `_parse_spotify_date`)
- Fixed genre playlist links to use `open_url` with fallback chain
- Fixed genre playlist search (`genre:` filter removed — invalid for playlist searches)
- Set up fully local dev environment: backend `http://127.0.0.1:8000`, frontend `http://localhost:8080`
  - SQLite support added alongside PostgreSQL; auto-detects from `DATABASE_URL`
  - `load_dotenv(“backend/.env”)` for local config
  - Spotify OAuth confirmed working with `http://127.0.0.1:8000/auth/callback`
- Added **Recently Played** side card (5 default, expand to 25)
- Added **Artist Catalog Depth** with live fuzzy search and album grid with saved/unsaved status
- Added **Genre Breakdown** pie chart sourced from liked songs (scans up to 1,000 tracks)
- Added **Mood Timeline** line chart (energy/valence/danceability/acousticness across 3 time ranges)
  - Graceful fallback for deprecated `audio_features` endpoint (apps created after Nov 2024)

## Current Known Issues

- Mood Timeline may show “unavailable” if Spotify app was created after Nov 27, 2024 (audio_features deprecated).
- Genre Breakdown scans up to 1,000 liked songs — may be slow on first load for large libraries.
- Artist Catalog Depth only includes studio albums (no singles/EPs/compilations by design).

## Next Debug Tasks

- Validate genre playlist recommendations in production contain correct `open_url` values.
- Test `added_7d` / `added_30d` fix in production (was already fixed locally).

## Future Additions

### Dashboard
- **Listening Heatmap** — GitHub-style calendar of tracks added per day over the last year
- **Duplicate Track Detector** — scan all playlists for the same track appearing in multiple playlists
- **Playlist Overlap Matrix** — show which playlists share the most tracks with each other
- **New Release Radar** — check followed artists for albums released in the last 30/60/90 days that you haven't saved
- **Listening Streak** — consecutive days with at least one new track added or played
- **Library Health Score** — composite score based on genre diversity, recency of adds, catalog depth, etc.
- **Top Collaborators** — artists who appear most often alongside your top artists on tracks you've saved

### Playlist Tools
- **Smart Playlist Builder** — create playlists from filters (genre, BPM range, year range, popularity)
- **Playlist Merger** — merge two or more playlists, deduplicate, and optionally archive originals
- **Optional “Open All Picks” Export** — save genre playlist recommendations into a new Spotify playlist
- **Playlist Age Audit** — show which playlists haven't been updated in 6+ months
- **Auto-Tag Manager** — UI to view and edit automation tags (`[spotipy:...]`) across all playlists

### Profile & Organization
- **Usage Analytics Card** — last sync times, script success/failure counts, total runs
- **Safer Run Controls** — rate-limit-aware retries with queue indicator
- **Enhanced Onboarding** — step-by-step Spotify connect + first-run wizard
- **Artist Follow Gap** — artists you have saved tracks from but are not following
- **Genre Tag Auto-Assign** — propose genre tags for untagged playlists based on their track content
