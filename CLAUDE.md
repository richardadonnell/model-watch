# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A static dashboard aggregating frontier-LLM scores/prices from a few leaderboard APIs. A Python pipeline (`modelwatch/`) writes `data/*.json`; a vanilla-JS site at the repo root renders them. A daily GitHub Action refreshes the data and commits it; GitHub Pages serves the site. No frontend build step. See `README.md` for the architecture diagram.

## Commands (Windows)

- Tests: `.venv/Scripts/python.exe -m pytest` (Python 3.12 venv; deps in `requirements.txt`)
- Build data locally: `.venv/Scripts/python.exe -m modelwatch.build` (makes live API calls; sources without keys fail-soft to empty)
- Preview site: `.venv/Scripts/python.exe -m http.server 8000` from repo root
- JS is unbundled — sanity-check with `node --check app.js`

## Architecture rules

- **Fetcher contract:** each `modelwatch/fetchers/<source>.py` exposes `SOURCE_ID`, a pure `parse(...)`, and `fetch() -> {"entries": [{"raw_name", "metrics"}], "data_date": str|None}`. Keep `parse` pure (no network) so it's unit-tested on sample payloads; `fetch` is the thin I/O wrapper. `data_date` is the source's own data date (Aider max entry date, LiveBench release-filename date); live sources use `None`.
- **Fail-soft is non-negotiable:** a fetch failure must never fail the build. `run_fetchers` catches per-source and returns `None`; `build_snapshot` carries the last-good scores forward and stamps `stale_since`. Preserve this when editing the pipeline.
- **Prices are normalized to USD per 1M tokens** across sources (OpenRouter returns per-token — multiply by 1e6; Artificial Analysis returns per-1M).
- **Model list is a curated shortlist** in `models.yaml` (id + per-source `aliases`). Sources report hundreds of names; only aliased ones are tracked. Unmatched names are logged to `unmatched.txt` (uploaded as an Action artifact) — that's the signal for what to add. Do NOT switch to auto-tracking every model.
- **`data/` is committed, not gitignored** — it IS the site's content and the trend history (`data/history/`). Don't add it to `.gitignore`.

## Frontend / UI

- **Read `.impeccable.md` before any UI work** — it holds the design context (audience, tone, principles). The site is a deliberate "telemetry-instrument" aesthetic, dark, and must NOT drift toward the generic AI-dashboard look (no cyan/purple, gradients, glow, or glass).
- **Type:** `Saira Semi Condensed` for labels/headers + `Geist Mono` for all numerals (loaded from Google Fonts in `index.html`). Numeric table columns get mono via a CSS positional selector (`td:not(:first-child):not(:nth-child(2))`) so digits align — the column order in `METRIC_COLS` (`app.js`) maps to those columns. Don't reintroduce system fonts.
- **Color:** OKLCH tokens live in `styles.css :root`. One rare amber `--accent` carries meaning only (active sort, live dot, chart callouts) — don't spread it around. Neutrals are tinted warm; no pure `#000`/`#fff`.

## Gotchas

- **`.nojekyll` at the repo root is required** — GitHub Pages runs Jekyll by default and chokes on `vendor/` and `data/`. Never delete it.
- **Chart.js can't parse `oklch()`** — its color engine only takes hex/rgb. The chart palette is a hardcoded hex map (`const C`) in `app.js renderCharts`, kept in sync with the CSS tokens by hand. Keep chart colors as hex; do NOT swap them to `var(--token)` or the marks silently disappear.
- **OpenRouter usage** comes from an undocumented `api/frontend/v1/rankings/models` endpoint — it can break without notice. It's fail-soft, but expect it may need re-checking.
- **Secrets:** the Action reads `ARTIFICIALANALYSIS_API_KEY` (repo Actions secret). Never hardcode keys. Artificial Analysis requires attribution — the link in the site footer must stay.
- API-sourced strings (model names) are escaped before HTML interpolation in `app.js` (`esc()`) and before markdown tables — keep new interpolations escaped.

## Workflow

- Conventional commits; work directly on `main` (solo deployed repo, no PRs).
- After pipeline changes, run the full `pytest` suite before committing; keep tests passing.
- The daily Action (`.github/workflows/build.yml`) runs pytest → build → commit data → push, and on Mondays upserts a "🔭 New model suggestions" issue from `data/suggestions.json`.
