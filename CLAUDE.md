# Claude Code Configuration — Spotipy Scripts

## At Session Start

1. Read `STATUS.md` — canonical current state (frontmatter + prose).
2. Read `ROADMAP.md` for planned features (last meaningful entry sits at the top).

## Dashboard Frontmatter Discipline (NON-NEGOTIABLE)

The personal dashboard at `~/Documents/dev/dashboard/` reads `STATUS.md` frontmatter to surface this project's status. **When you make meaningful changes (ship a feature, deploy a fix, kill something, change the roadmap), update the frontmatter at wrap-up.**

Required updates whenever state changes meaningfully:
- `last_meaningful_change: YYYY-MM-DD` — today's date in ISO format
- `summary: "..."` — one-line current state (surfaced on the dashboard card)
- `lifecycle:` — only update if the project moved between dev/trial/live/paused/legacy/unclassified
- `lifecycle_changed_at: YYYY-MM-DD` — bump ONLY when `lifecycle` itself changed
- `runtime:` — running/stopped/unknown/not_applicable; update if real status changed
- `health:` — ok/warn/critical/unknown; update if material issues changed
- `host:` — if it moved (render+github-pages, etc.)

**Hero-banner fields:**
- `action_status:` — `running_no_action` / `waiting` / `needs_action` / `blocked`
- `next_action:` — one short imperative sentence
- `waiting_until:` — ISO date OR free-form text

Optional but valuable:
- `metrics:` — list of `{label, value, unit?, trend?, as_of?}` for KPIs surfaced on the detail page (e.g., scripts deployed, songs in vault, last successful workflow run)

**Stale-but-honest > fresh-but-misleading.** If you just read the project but changed nothing meaningful, don't bump dates.

Schema: `~/Documents/dev/dashboard/lib/schema/snapshot.ts`.

## Architecture (quick reference)

- `backend/` — FastAPI on Render. Routes: `/stats/*`, `/automation/*`, `/recommendations/*`. New routes require manual Render deploy.
- `website/` — Vite + React + TypeScript. Deployed to GitHub Pages via Actions workflow.
- `scripts/` — Python automation: `vaulted_add`, `liked_add`, `monthly_recommend`. Per-script env + cache under `.cache/`.
- `liked.bat` / `vaulted.bat` / `*.ps1` — Windows runners (Joe runs from PC sometimes).

## Behavioral Rules

- NEVER hardcode Spotify credentials; they live in `.env` (gitignored).
- NEVER commit `.cache/` (OAuth tokens).
- Prefer editing existing files; don't sprinkle new ones.
