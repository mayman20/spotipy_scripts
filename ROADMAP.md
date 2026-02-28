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

## Current Known Issues

- `Added Last 7 Days` and `Added Last 30 Days` counters are still not reliably reflecting expected values in the deployed dashboard.
- Genre recommendation cards are still not consistently opening/using the expected Spotify playlist links in deployed behavior.
- These issues are confirmed by user testing as of 2026-02-28 and require another debugging pass.

## Next Debug Tasks

- Add backend debug logging around saved-track `added_at` parsing/count windows and verify timezone/date cutoff logic in production.
- Add a temporary diagnostics endpoint for count verification (`added_7d`, `added_30d`, sample `added_at` values).
- Verify frontend is reading the latest deployed API responses (cache invalidation/hard-refresh/deploy drift checks).
- Validate genre recommendation payload in production contains playlist `id`, `url`, and `open_url` for each card.
- Force frontend to use one canonical field for links and add fallback rendering when link fields are missing.

## Future Additions

- Listening-history visuals (genre trend chart, artist share chart, track frequency heatmap)
- Optional “Open all picks” playlist export flow (save recommended genre picks into a new playlist)
- Usage analytics card (last sync times, script success/failure counts)
- Safer run controls (rate-limit aware retries + queue indicator)
- Enhanced onboarding for first-time users (step-by-step Spotify connect + first run wizard)
