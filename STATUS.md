---
project_id: spotify-scripts
title: Spotify Scripts + Web Dashboard
lifecycle: live
runtime: running
data_state: not_applicable
health: warn
host: render+github-pages
last_meaningful_change: 2026-03-07
lifecycle_changed_at: 2026-02-28
action_status: needs_action
next_action: "Audit Render backend route deployment gaps; ship Listening Pattern Explorer (P1 roadmap item)."
summary: "Playlist automation (vaulted_add, liked_add, monthly_recommend) + React/Vite dashboard on GitHub Pages backed by FastAPI on Render. Live but ROADMAP.md is stale since 2026-03-07; backend route gaps not fully audited."
tags:
  - web-app
  - FastAPI
  - React-Vite
  - OAuth
  - GitHub-Pages
  - Render
---

# Spotify Scripts + Web Dashboard — Status

## What's live

- **Frontend**: React + Vite, deployed to GitHub Pages.
- **Backend**: FastAPI on Render, OAuth + endpoints under `/stats/*`, `/automation/*`, `/recommendations/*`.
- **Automation scripts**: `scripts/vaulted_add`, `scripts/liked_add`, `scripts/monthly_recommend`. Runners exist as `*.bat` (Windows) and `*.ps1` (PowerShell).
- **Last verified deploy**: commit `22b903e` synced 2026-03-07, GitHub Pages workflow `22801166898` succeeded.

## Known issues (from ROADMAP.md, last meaningful entry 2026-03-07)

- `audio_features` Spotify endpoint deprecated — affects parts of monthly_recommend.
- Genre-breakdown is slow on large libraries.
- Auto-remove-from-source toggle on dashboard is UI-only, no backend wired.
- Backend route deployment cadence is manual (Render doesn't auto-sync new routes from main).

## Canonical URLs

- **Frontend**: (fill in when probe added in Phase 7)
- **Backend health**: (fill in `/health` URL when probe added in Phase 7)
- **GitHub repo**: (fill in when probe added)

## Roadmap (next items, from ROADMAP.md)

1. Backend route sync — ensure new endpoints are live on Render.
2. Listening Pattern Explorer (priority feature #1 in ROADMAP).
3. Genre Drift Timeline (priority feature #2).
4. Six more priority features in ROADMAP.md.

## Update protocol

When this file is touched (lifecycle change, deploy, feature ships, issue resolved), bump the frontmatter and add a one-line entry below. Update mtime ≥ once / 14 days to keep dashboard freshness `fresh`.

## Change log

- **2026-05-13** — File created by dashboard initialization. Inferred lifecycle=live (deployed + reachable per ROADMAP 2026-03-07 entry), health=warn (stale roadmap, known unresolved gaps).
