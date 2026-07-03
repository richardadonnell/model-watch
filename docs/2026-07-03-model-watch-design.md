# model-watch — Design Spec

Date: 2026-07-03
Status: approved (design), pending spec review
Target repo: new public repo `richardadonnell/model-watch` (this doc lives in personal-assistant until that repo exists, then moves with the code)

## Purpose

Single dashboard page that shows the current state of frontier LLMs — scores, rankings, prices — aggregated daily from a handful of reliable leaderboard sources, plus a "what changed" feed. Replaces manually checking ~24 leaderboard sites.

## Decisions (from brainstorm)

| Question | Decision |
|---|---|
| Core job | Live aggregated dashboard |
| Data strategy | Few reliable sources, deep (API/stable-JSON only; no scraping hostile sites) |
| Hosting | Static site, GitHub Pages, daily scheduled GitHub Action rebuild |
| Views | All four: changes feed, model table, source cards, price/perf charts |
| Model scope | Curated frontier shortlist (~15-25), hand-maintained `models.yaml` |
| Cadence | Daily, with history snapshots kept for trends |
| Alerts | None — page only |
| Stack | Plain static: Python fetch script → JSON; single HTML + vanilla JS + one chart lib |
| Repo | New public GitHub repo |

## Architecture

```
GitHub Action (cron daily)
  └─ fetch.py
       ├─ source fetchers (one module per source)
       ├─ normalize model names against models.yaml
       ├─ write data/latest.json
       ├─ write data/history/YYYY-MM-DD.json
       └─ commit → GitHub Pages redeploys

index.html + app.js + chart lib
  └─ reads data/latest.json (+ history for sparklines/diffs)
```

## Data sources

Candidate sources — **implementation task #1 is verifying each has a stable, permitted data feed before building on it.** Drop any that don't; the site must degrade gracefully to fewer sources.

| Source | Expected feed | Status |
|---|---|---|
| OpenRouter | Public API (models, pricing; rankings TBD) | verify |
| Artificial Analysis | Official API (free tier w/ attribution) | verify terms |
| Aider leaderboard | YAML data files in aider GitHub repo | verify path |
| LiveBench | Published results (GitHub/HF) | verify |
| HF Open LLM Leaderboard | HF datasets API | verify |
| llm-stats | Unknown | verify or drop |

Scrape-hostile / no-feed sources (LMArena, Scale SEAL, SWE-bench site, etc.) are NOT fetched — they appear as link-only cards preserving the full 24-site tiered launchpad list.

## Components

### fetch.py (+ per-source fetcher modules)

- Each fetcher: `fetch() -> list[SourceScore]` — pure fetch + parse, no cross-source logic
- Failure isolation: a fetcher raising ⇒ that source keeps last-good data, stamped `stale_since`; build never fails wholesale
- Name normalization: map source-specific model names → canonical IDs in `models.yaml`; unmatched names logged to `unmatched.txt` (Action artifact) for shortlist maintenance

### models.yaml

- Hand-maintained canonical shortlist: id, display name, vendor, aliases (per-source name variants)

### data/

- `latest.json` — canonical current dataset (models × sources, prices, timestamps, staleness)
- `history/YYYY-MM-DD.json` — daily snapshots, committed, powers diffs + trends

### Site (index.html, app.js, styles.css, vendored chart lib)

1. **Changes feed** (top) — diff latest vs previous snapshot: new models, rank moves, notable price changes
2. **Model table** — one row per shortlist model; columns = per-source scores + price; client-side sortable
3. **Source cards** — grouped by tier (from Richard's 24-site list); fetched sources show top-5 + last-updated; others link-only
4. **Charts** — intelligence-vs-price scatter; per-model trend sparklines from history

No build step for the site itself — static files served as-is by Pages.

## Infra

- Public repo `richardadonnell/model-watch`
- GitHub Pages from main branch
- Action: daily cron → run fetch.py → commit data → Pages auto-deploy
- Secrets: API keys (e.g. ARTIFICIAL_ANALYSIS_API_KEY) as repo Actions secrets — never committed

## Error handling

- Per-source failure → last-good data + "stale since X" badge on that source's card/columns
- All sources fail → site still renders with previous data; Action logs failure
- Diff logic tolerant of missing prior snapshot (first run ⇒ empty changes feed)

## Testing

- pytest: name normalization (aliases, unmatched), diff logic (new/moved/removed), snapshot parse/serialize round-trip
- Fetchers verified against live endpoints during development; thin parsers unit-tested on saved sample payloads

## Out of scope (YAGNI)

Alerts/notifications, auth, database, JS framework, scraping hostile sites, intra-day refresh, tracking every model.
