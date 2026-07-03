# model-watch

A daily-updated dashboard that aggregates frontier LLM scores, rankings, and
prices from a handful of reliable leaderboard sources into one page — so you
can see the state of the art without checking a dozen sites.

**Live:** https://richardadonnell.github.io/model-watch/

## What it shows

- **Model table** — one row per tracked model, columns of scores/prices across
  every source, client-side sortable.
- **What-changed feed** — new models and rank movements versus the previous
  daily snapshot.
- **Leaderboard cards** — grouped by tier; fetched sources show their current
  top 5, and the full launchpad list of ~20 leaderboards is linked for the
  sources that have no machine-readable feed.
- **Charts** — intelligence-vs-price scatter and per-model trend sparklines
  built from the daily history.

## Data sources

Only sources with a stable, permitted feed are fetched; everything else is a
link-only card.

| Source | Data | Auth |
|---|---|---|
| [OpenRouter](https://openrouter.ai/) | Model list, pricing, real usage rankings | none |
| [Aider](https://aider.chat/docs/leaderboards/) | Polyglot code-editing pass rate | none |
| [LiveBench](https://livebench.ai/) | Contamination-resistant benchmark scores | none |
| [Artificial Analysis](https://artificialanalysis.ai/) | Intelligence/coding index, price, speed | API key |
| [llm-stats](https://llm-stats.com/) | TrueSkill-style ratings | API key |

Prices are normalized to USD per 1M tokens across sources. Every source is
failure-isolated: if one feed is down, its last-good data is kept and stamped
"stale", and the build never fails as a whole.

## How it works

```
GitHub Action (daily cron)
  └─ python -m modelwatch.build
       ├─ fetch each source (fail-soft)          modelwatch/fetchers/*.py
       ├─ normalize model names → models.yaml    modelwatch/registry.py
       ├─ build snapshot + diff vs yesterday     modelwatch/snapshot.py, diff.py
       ├─ write data/latest.json, data/history/, data/trends.json
       └─ commit data → GitHub Pages redeploys

index.html + app.js + vendored Chart.js  →  reads data/*.json (no build step)
```

- `models.yaml` — hand-curated shortlist of tracked models, with per-source
  name aliases. Unmatched names from each run are logged to `unmatched.txt`.
- `sources.yaml` — the full tiered launchpad list rendered as cards.
- `data/history/YYYY-MM-DD.json` — daily snapshots that power the diff feed and
  trend sparklines.

## Development

```bash
python -m venv .venv && .venv/Scripts/activate    # Windows; use bin/activate on Unix
pip install -r requirements.txt
python -m pytest                                   # 29 tests
python -m modelwatch.build                         # writes data/*.json locally
python -m http.server 8000                         # then open http://localhost:8000
```

The Artificial Analysis and llm-stats fetchers read `ARTIFICIALANALYSIS_API_KEY`
and `LLMSTATS_API_KEY` from the environment (repo Actions secrets in CI). Without
them those two sources fail-soft and their columns stay empty; the other three
sources still render.

## Attribution

Intelligence, speed, and price data by
[Artificial Analysis](https://artificialanalysis.ai/). Usage data by
[OpenRouter](https://openrouter.ai/rankings).
