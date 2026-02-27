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
