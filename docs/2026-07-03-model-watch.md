# model-watch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Static dashboard site (GitHub Pages) showing current frontier-LLM scores/prices aggregated daily from 5 verified sources, with a what-changed feed, model table, tiered source cards, and charts.

**Architecture:** Python package `modelwatch` fetches each source (failure-isolated), normalizes model names against a hand-curated `models.yaml`, writes `data/latest.json` + dated history snapshot + `data/trends.json`; a GitHub Action runs it daily and commits. The site is plain static files at repo root (index.html + app.js + vendored Chart.js) reading those JSON files.

**Tech Stack:** Python 3.12 (requests, PyYAML, pytest), vanilla JS, Chart.js (vendored UMD single file), GitHub Actions + Pages.

**Working directory:** NEW repo at `C:\Users\richa\projects\model-watch` (created in Task 1). All paths below relative to that repo root. Spec: `personal-assistant/docs/superpowers/specs/2026-07-03-model-watch-design.md`.

## Global Constraints

- Sources fetched (verified 2026-07-03): OpenRouter (`https://openrouter.ai/api/v1/models`, no auth; rankings `https://openrouter.ai/api/frontend/v1/rankings/models`, no auth, undocumented), Artificial Analysis (`https://artificialanalysis.ai/api/v2/data/llms/models`, header `x-api-key`, 1000 req/day, attribution link required on site), Aider (`https://raw.githubusercontent.com/Aider-AI/aider/main/aider/website/_data/polyglot_leaderboard.yml`), LiveBench (CSV in `livebench/livebench.github.io` repo `public/table_<release>.csv`, release discovered via GitHub contents API, current `2026_01_08`), llm-stats (`https://api.llm-stats.com/stats/v1/...`, Bearer key).
- HF Open LLM Leaderboard is NOT fetched (frozen Mar 2025) — link-only card.
- Unit rule: all prices normalized to **USD per 1M tokens**. OpenRouter returns per-token (multiply by 1_000_000); AA returns per-1M already.
- A fetcher failure must never fail the build: keep last-good data for that source, stamp `stale_since`.
- No secrets in code or committed files. Env vars: `ARTIFICIALANALYSIS_API_KEY`, `LLMSTATS_API_KEY`.
- Aider headline metric = `pass_rate_2`.
- Site must render with zero build step (static files only) and must show the full 24-site tiered launchpad list (link-only for unfetched sources).
- Site footer must include attribution link to `https://artificialanalysis.ai/`.
- Conventional commits.

---

### Task 1: Repo scaffold

**Files:**
- Create: `C:\Users\richa\projects\model-watch\` (git init), `README.md`, `.gitignore`, `requirements.txt`, `pytest.ini`, `modelwatch/__init__.py`, `tests/__init__.py`

**Interfaces:**
- Produces: repo skeleton; `requirements.txt` with `requests`, `PyYAML`, `pytest`.

- [ ] **Step 1: Create repo + venv**

```bash
mkdir -p /c/Users/richa/projects/model-watch && cd /c/Users/richa/projects/model-watch
git init -b main
py -3.12 -m venv .venv || py -3 -m venv .venv
.venv/Scripts/python.exe -m pip install requests PyYAML pytest
```

- [ ] **Step 2: Write files**

`requirements.txt`:
```
requests>=2.31
PyYAML>=6.0
pytest>=8.0
```

`.gitignore`:
```
.venv/
__pycache__/
unmatched.txt
```

`pytest.ini`:
```ini
[pytest]
testpaths = tests
```

`README.md`:
```markdown
# model-watch

Daily-updated dashboard of frontier LLM scores and prices, aggregated from
OpenRouter, Artificial Analysis, Aider, LiveBench, and llm-stats.
Static site on GitHub Pages; data refreshed by a scheduled GitHub Action.

Intelligence/speed/price data by [Artificial Analysis](https://artificialanalysis.ai/).
```

Empty `modelwatch/__init__.py`, `tests/__init__.py`.

- [ ] **Step 3: Verify pytest runs**

Run: `.venv/Scripts/python.exe -m pytest`
Expected: "no tests ran" exit (collected 0 items) — no errors.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "chore: scaffold repo"
```

---

### Task 2: Model registry + name normalization

**Files:**
- Create: `models.yaml`, `modelwatch/registry.py`
- Test: `tests/test_registry.py`

**Interfaces:**
- Produces: `load_registry(path: str) -> Registry`; `Registry.models -> list[dict]` (each: `id`, `name`, `vendor`, `aliases`); `Registry.canonical_id(source_id: str, raw_name: str) -> str | None`.

- [ ] **Step 1: Write failing tests**

`tests/test_registry.py`:
```python
from modelwatch.registry import load_registry

def test_alias_match(tmp_path):
    p = tmp_path / "models.yaml"
    p.write_text("""
models:
  - id: claude-sonnet-5
    name: Claude Sonnet 5
    vendor: Anthropic
    aliases:
      openrouter: ["anthropic/claude-sonnet-5"]
""")
    reg = load_registry(str(p))
    assert reg.canonical_id("openrouter", "anthropic/claude-sonnet-5") == "claude-sonnet-5"

def test_fallback_matches_id_and_name_case_insensitive(tmp_path):
    p = tmp_path / "models.yaml"
    p.write_text("""
models:
  - id: gpt-5
    name: GPT-5
    vendor: OpenAI
    aliases: {}
""")
    reg = load_registry(str(p))
    assert reg.canonical_id("livebench", "GPT-5") == "gpt-5"
    assert reg.canonical_id("aider", "gpt-5") == "gpt-5"

def test_unmatched_returns_none(tmp_path):
    p = tmp_path / "models.yaml"
    p.write_text("models:\n  - id: gpt-5\n    name: GPT-5\n    vendor: OpenAI\n    aliases: {}\n")
    reg = load_registry(str(p))
    assert reg.canonical_id("openrouter", "some/unknown-model") is None
```

- [ ] **Step 2: Run tests, verify FAIL** — `.venv/Scripts/python.exe -m pytest tests/test_registry.py -v` → ModuleNotFoundError/ImportError.

- [ ] **Step 3: Implement**

`modelwatch/registry.py`:
```python
import yaml


def _norm(s: str) -> str:
    return s.strip().lower()


class Registry:
    def __init__(self, models: list[dict]):
        self.models = models
        # lookup[(source_id, normalized_alias)] -> canonical id; source_id "*" = any source
        self._lookup: dict[tuple[str, str], str] = {}
        for m in models:
            for source_id, names in (m.get("aliases") or {}).items():
                for n in names:
                    self._lookup[(source_id, _norm(n))] = m["id"]
            self._lookup[("*", _norm(m["id"]))] = m["id"]
            self._lookup[("*", _norm(m["name"]))] = m["id"]

    def canonical_id(self, source_id: str, raw_name: str) -> str | None:
        key = _norm(raw_name)
        return self._lookup.get((source_id, key)) or self._lookup.get(("*", key))


def load_registry(path: str) -> Registry:
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return Registry(doc["models"])
```

- [ ] **Step 4: Run tests, verify PASS** — same pytest command.

- [ ] **Step 5: Seed `models.yaml`**

Create `models.yaml` with a frontier shortlist. Populate aliases from the live sources during Task 9 (first real run logs unmatched names); seed with best-known slugs now — every entry must at least have `id`, `name`, `vendor`:

```yaml
# Canonical frontier shortlist. aliases: per-source raw names as they appear in that source's feed.
models:
  - id: claude-fable-5
    name: Claude Fable 5
    vendor: Anthropic
    aliases: {openrouter: ["anthropic/claude-fable-5"]}
  - id: claude-opus-4.8
    name: Claude Opus 4.8
    vendor: Anthropic
    aliases: {openrouter: ["anthropic/claude-opus-4.8"]}
  - id: claude-sonnet-5
    name: Claude Sonnet 5
    vendor: Anthropic
    aliases: {openrouter: ["anthropic/claude-sonnet-5"]}
  - id: claude-haiku-4.5
    name: Claude Haiku 4.5
    vendor: Anthropic
    aliases: {openrouter: ["anthropic/claude-haiku-4.5"]}
  - id: gpt-5
    name: GPT-5
    vendor: OpenAI
    aliases: {openrouter: ["openai/gpt-5"]}
  - id: gemini-2.5-pro
    name: Gemini 2.5 Pro
    vendor: Google
    aliases: {openrouter: ["google/gemini-2.5-pro"]}
  - id: grok-4
    name: Grok 4
    vendor: xAI
    aliases: {openrouter: ["x-ai/grok-4"]}
  - id: deepseek-r1
    name: DeepSeek R1
    vendor: DeepSeek
    aliases: {openrouter: ["deepseek/deepseek-r1"]}
  - id: qwen3-235b
    name: Qwen3 235B
    vendor: Alibaba
    aliases: {openrouter: ["qwen/qwen3-235b-a22b"]}
  - id: llama-4-maverick
    name: Llama 4 Maverick
    vendor: Meta
    aliases: {openrouter: ["meta-llama/llama-4-maverick"]}
  - id: mistral-large
    name: Mistral Large
    vendor: Mistral
    aliases: {openrouter: ["mistralai/mistral-large"]}
  - id: kimi-k2
    name: Kimi K2
    vendor: Moonshot
    aliases: {openrouter: ["moonshotai/kimi-k2"]}
```

(These OpenRouter slugs are best-effort seeds — Task 9's unmatched log is the authoritative correction loop. Extend the list there with whatever current frontier models the feeds actually report.)

- [ ] **Step 6: Commit** — `git add -A && git commit -m "feat: model registry with alias normalization"`

---

### Task 3: Source metadata (tiers + launchpad list)

**Files:**
- Create: `sources.yaml`
- Test: `tests/test_sources.py`

**Interfaces:**
- Produces: `sources.yaml` — list of ALL 24 launchpad sites with `id`, `name`, `url`, `tier` (1-6), `tier_name`, `note`, `fetched` (bool). The 5 fetched ids: `openrouter`, `artificialanalysis`, `aider`, `livebench`, `llmstats`.

- [ ] **Step 1: Write failing test**

`tests/test_sources.py`:
```python
import yaml

def test_sources_yaml_valid():
    with open("sources.yaml", encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    sources = doc["sources"]
    assert len(sources) >= 24
    fetched = {s["id"] for s in sources if s.get("fetched")}
    assert fetched == {"openrouter", "artificialanalysis", "aider", "livebench", "llmstats"}
    for s in sources:
        assert s["url"].startswith("https://")
        assert s["tier"] in range(1, 7)
```

- [ ] **Step 2: Run, verify FAIL** (file missing).

- [ ] **Step 3: Create `sources.yaml`** — all 24 sites from Richard's tier list (Tier 1: artificialanalysis, openrouter, llm-stats, livebench; Tier 2: swebench, aider, livecodebench, tbench, swebench-pro, deepswe; Tier 3: lmarena, arena-ai; Tier 4: arcprize, simple-bench, scale-seal; Tier 5: vellum, benchlm; Tier 6: models-dev, epochai, vals-ai, hf-open-llm) with `fetched: true` only on the 5. Copy names/urls/notes verbatim from the spec's source list (Untitled-22 content is embedded in the design discussion; urls: artificialanalysis.ai, openrouter.ai/rankings, llm-stats.com, livebench.ai, swebench.com, aider.chat/docs/leaderboards/, livecodebench.github.io/leaderboard.html, tbench.ai, scale.com/leaderboard/swe_bench_pro_public, deepswe.datacurve.ai, lmarena.ai, arena.ai/leaderboard/, arcprize.org/leaderboard, simple-bench.com, labs.scale.com/leaderboard, vellum.ai/llm-leaderboard, benchlm.ai, models.dev, epochai.org, vals.ai, huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard). That's 21 distinct sites; also add hf note "frozen Mar 2025". Adjust the test count to the actual number (>= 21).

Example entry shape:
```yaml
sources:
  - id: artificialanalysis
    name: Artificial Analysis
    url: https://artificialanalysis.ai/
    tier: 1
    tier_name: Daily drivers
    note: Best methodology; intelligence/speed/price in one place
    fetched: true
```

- [ ] **Step 4: Run test, verify PASS.**
- [ ] **Step 5: Commit** — `git commit -am "feat: source metadata with tiers"`

---

### Task 4: Fetchers — OpenRouter + Artificial Analysis

**Files:**
- Create: `modelwatch/fetchers/__init__.py`, `modelwatch/fetchers/openrouter.py`, `modelwatch/fetchers/artificialanalysis.py`
- Test: `tests/test_fetch_parsers.py`

**Interfaces:**
- Produces: each fetcher module exposes `SOURCE_ID: str` and `fetch() -> list[dict]` where each dict = `{"raw_name": str, "metrics": dict[str, float|int|None]}`. Parsing split into pure `parse(payload) -> list[dict]` for testability. Env: `ARTIFICIALANALYSIS_API_KEY`.

- [ ] **Step 1: Write failing parser tests** (sample payloads mirror verified live shapes)

`tests/test_fetch_parsers.py`:
```python
from modelwatch.fetchers import openrouter, artificialanalysis

OR_MODELS = {"data": [{
    "id": "anthropic/claude-sonnet-5", "name": "Anthropic: Claude Sonnet 5",
    "context_length": 1000000,
    "pricing": {"prompt": "0.000002", "completion": "0.00001"},
}]}
OR_RANKINGS = {"data": [
    {"date": "2026-07-02", "model_permaslug": "anthropic/claude-sonnet-5",
     "total_completion_tokens": 5, "total_prompt_tokens": 95, "count": 3},
    {"date": "2026-07-02", "model_permaslug": "openai/gpt-5",
     "total_completion_tokens": 10, "total_prompt_tokens": 40, "count": 2},
]}

def test_openrouter_parse_normalizes_price_per_million():
    rows = openrouter.parse(OR_MODELS, OR_RANKINGS)
    row = next(r for r in rows if r["raw_name"] == "anthropic/claude-sonnet-5")
    assert row["metrics"]["price_in_per_1m"] == 2.0
    assert row["metrics"]["price_out_per_1m"] == 10.0
    assert row["metrics"]["tokens_total"] == 100
    assert row["metrics"]["context_length"] == 1000000

AA = {"status": 200, "data": [{
    "id": "uuid-1", "name": "Claude Sonnet 5", "slug": "claude-sonnet-5",
    "model_creator": {"name": "Anthropic"},
    "evaluations": {"artificial_analysis_intelligence_index": 70.1,
                    "artificial_analysis_coding_index": 65.2},
    "pricing": {"price_1m_input_tokens": 2.0, "price_1m_output_tokens": 10.0,
                "price_1m_blended_3_to_1": 4.0},
    "median_output_tokens_per_second": 80.5,
    "median_time_to_first_token_seconds": 0.6,
}]}

def test_aa_parse():
    rows = artificialanalysis.parse(AA)
    m = rows[0]["metrics"]
    assert rows[0]["raw_name"] == "claude-sonnet-5"
    assert m["intelligence_index"] == 70.1
    assert m["coding_index"] == 65.2
    assert m["price_blended_per_1m"] == 4.0
    assert m["tokens_per_second"] == 80.5
```

- [ ] **Step 2: Run, verify FAIL.**

- [ ] **Step 3: Implement**

`modelwatch/fetchers/__init__.py`: empty.

`modelwatch/fetchers/openrouter.py`:
```python
import requests

SOURCE_ID = "openrouter"
MODELS_URL = "https://openrouter.ai/api/v1/models"
# Undocumented frontend endpoint (verified 2026-07-03) — may break without notice.
RANKINGS_URL = "https://openrouter.ai/api/frontend/v1/rankings/models"


def parse(models_payload: dict, rankings_payload: dict) -> list[dict]:
    usage: dict[str, int] = {}
    for row in rankings_payload.get("data", []):
        slug = row.get("model_permaslug")
        if slug:
            usage[slug] = usage.get(slug, 0) + int(row.get("total_completion_tokens", 0)) \
                + int(row.get("total_prompt_tokens", 0))
    out = []
    for m in models_payload["data"]:
        p = m.get("pricing") or {}
        def per_1m(key):
            v = p.get(key)
            return round(float(v) * 1_000_000, 4) if v is not None else None
        out.append({
            "raw_name": m["id"],
            "metrics": {
                "price_in_per_1m": per_1m("prompt"),
                "price_out_per_1m": per_1m("completion"),
                "context_length": m.get("context_length"),
                "tokens_total": usage.get(m["id"]),
            },
        })
    return out


def fetch() -> list[dict]:
    models = requests.get(MODELS_URL, timeout=30)
    models.raise_for_status()
    rankings = requests.get(RANKINGS_URL, timeout=30)
    rankings.raise_for_status()
    return parse(models.json(), rankings.json())
```

`modelwatch/fetchers/artificialanalysis.py`:
```python
import os
import requests

SOURCE_ID = "artificialanalysis"
URL = "https://artificialanalysis.ai/api/v2/data/llms/models"


def parse(payload: dict) -> list[dict]:
    out = []
    for m in payload["data"]:
        ev = m.get("evaluations") or {}
        pr = m.get("pricing") or {}
        out.append({
            "raw_name": m["slug"],
            "metrics": {
                "intelligence_index": ev.get("artificial_analysis_intelligence_index"),
                "coding_index": ev.get("artificial_analysis_coding_index"),
                "price_in_per_1m": pr.get("price_1m_input_tokens"),
                "price_out_per_1m": pr.get("price_1m_output_tokens"),
                "price_blended_per_1m": pr.get("price_1m_blended_3_to_1"),
                "tokens_per_second": m.get("median_output_tokens_per_second"),
                "ttft_seconds": m.get("median_time_to_first_token_seconds"),
            },
        })
    return out


def fetch() -> list[dict]:
    key = os.environ["ARTIFICIALANALYSIS_API_KEY"]
    r = requests.get(URL, headers={"x-api-key": key}, timeout=30)
    r.raise_for_status()
    return parse(r.json())
```

- [ ] **Step 4: Run tests, verify PASS.**
- [ ] **Step 5: Commit** — `git commit -am "feat: openrouter + artificialanalysis fetchers"`

---

### Task 5: Fetchers — Aider + LiveBench + llm-stats

**Files:**
- Create: `modelwatch/fetchers/aider.py`, `modelwatch/fetchers/livebench.py`, `modelwatch/fetchers/llmstats.py`
- Modify (append tests): `tests/test_fetch_parsers.py`

**Interfaces:**
- Same fetcher contract as Task 4. Env: `LLMSTATS_API_KEY`. LiveBench fetcher must discover the newest `table_*.csv` via GitHub contents API.

- [ ] **Step 1: Write failing parser tests** (append to `tests/test_fetch_parsers.py`)

```python
from modelwatch.fetchers import aider, livebench, llmstats

AIDER_YAML = """
- dirname: 2026-06-01-x
  model: claude-sonnet-5
  edit_format: diff
  pass_rate_2: 82.2
  percent_cases_well_formed: 99.1
  total_cost: 12.34
  date: 2026-06-01
"""

def test_aider_parse():
    rows = aider.parse(AIDER_YAML)
    assert rows[0]["raw_name"] == "claude-sonnet-5"
    assert rows[0]["metrics"]["pass_rate"] == 82.2
    assert rows[0]["metrics"]["total_cost"] == 12.34

LB_CSV = "model,code_completion,code_generation,python\nclaude-sonnet-5,80.0,90.0,85.0\n"

def test_livebench_parse_averages_all_tasks():
    rows = livebench.parse(LB_CSV)
    assert rows[0]["raw_name"] == "claude-sonnet-5"
    assert rows[0]["metrics"]["average"] == 85.0

def test_livebench_pick_latest_release():
    files = [{"name": "table_2024_06_24.csv"}, {"name": "table_2026_01_08.csv"},
             {"name": "categories_2026_01_08.json"}]
    assert livebench.pick_latest_table(files) == "table_2026_01_08.csv"

LLMSTATS = {"data": [{"id": "claude-sonnet-5", "name": "Claude Sonnet 5",
                      "rating": 1310.5, "rank": 2}]}

def test_llmstats_parse():
    rows = llmstats.parse(LLMSTATS)
    assert rows[0]["raw_name"] == "claude-sonnet-5"
    assert rows[0]["metrics"]["rating"] == 1310.5
```

- [ ] **Step 2: Run, verify FAIL.**

- [ ] **Step 3: Implement**

`modelwatch/fetchers/aider.py`:
```python
import requests
import yaml

SOURCE_ID = "aider"
URL = "https://raw.githubusercontent.com/Aider-AI/aider/main/aider/website/_data/polyglot_leaderboard.yml"


def parse(text: str) -> list[dict]:
    out = []
    for e in yaml.safe_load(text) or []:
        out.append({
            "raw_name": str(e["model"]),
            "metrics": {
                "pass_rate": e.get("pass_rate_2"),
                "well_formed_pct": e.get("percent_cases_well_formed"),
                "total_cost": e.get("total_cost"),
            },
        })
    return out


def fetch() -> list[dict]:
    r = requests.get(URL, timeout=30)
    r.raise_for_status()
    return parse(r.text)
```

`modelwatch/fetchers/livebench.py`:
```python
import csv
import io
import requests

SOURCE_ID = "livebench"
LISTING_URL = "https://api.github.com/repos/livebench/livebench.github.io/contents/public"
RAW_BASE = "https://raw.githubusercontent.com/livebench/livebench.github.io/main/public/"


def pick_latest_table(files: list[dict]) -> str:
    tables = sorted(f["name"] for f in files
                    if f["name"].startswith("table_") and f["name"].endswith(".csv"))
    if not tables:
        raise ValueError("no livebench table found")
    return tables[-1]  # YYYY_MM_DD sorts lexicographically


def parse(csv_text: str) -> list[dict]:
    out = []
    for row in csv.DictReader(io.StringIO(csv_text)):
        name = row.pop("model")
        scores = [float(v) for v in row.values() if v not in ("", None)]
        avg = round(sum(scores) / len(scores), 2) if scores else None
        out.append({"raw_name": name, "metrics": {"average": avg}})
    return out


def fetch() -> list[dict]:
    listing = requests.get(LISTING_URL, timeout=30)
    listing.raise_for_status()
    table = pick_latest_table(listing.json())
    r = requests.get(RAW_BASE + table, timeout=30)
    r.raise_for_status()
    return parse(r.text)
```

`modelwatch/fetchers/llmstats.py`:
```python
import os
import requests

SOURCE_ID = "llmstats"
URL = "https://api.llm-stats.com/stats/v1/rankings"


def parse(payload: dict) -> list[dict]:
    out = []
    for m in payload.get("data", []):
        out.append({
            "raw_name": m.get("name") or m.get("id"),
            "metrics": {"rating": m.get("rating"), "rank": m.get("rank")},
        })
    return out


def fetch() -> list[dict]:
    key = os.environ["LLMSTATS_API_KEY"]
    r = requests.get(URL, headers={"Authorization": f"Bearer {key}"}, timeout=30)
    r.raise_for_status()
    return parse(r.json())
```

Implementation note: llm-stats response fields are the one unverified payload shape (agent verified endpoints + auth from docs, not a live authed response). During Task 9's live run, adjust `llmstats.parse` field names to the real payload and update the sample test to match. That's expected, not a failure.

- [ ] **Step 4: Run tests, verify PASS.**
- [ ] **Step 5: Commit** — `git commit -am "feat: aider, livebench, llmstats fetchers"`

---

### Task 6: Snapshot build + diff logic

**Files:**
- Create: `modelwatch/snapshot.py`, `modelwatch/diff.py`
- Test: `tests/test_snapshot.py`, `tests/test_diff.py`

**Interfaces:**
- Produces: `snapshot.build_snapshot(registry, results: dict[str, list[dict]], prev: dict | None, now_iso: str) -> tuple[dict, list[str]]` → `(snapshot, unmatched_names)`.
  Snapshot schema:
  ```json
  {
    "generated_at": "2026-07-03T12:00:00Z",
    "sources": {"openrouter": {"ok": true, "fetched_at": "...", "stale_since": null}},
    "models": {"claude-sonnet-5": {"name": "...", "vendor": "...",
               "scores": {"aider": {"pass_rate": 82.2}, ...}}},
    "ranks": {"aider": ["claude-sonnet-5", "gpt-5"]}
  }
  ```
- `diff.diff_snapshots(prev: dict | None, curr: dict) -> list[dict]` — events `{"type": "new_model"|"rank_change"|"source_stale", ...}`.
- Rank metric per source (hardcoded map in snapshot.py): openrouter→`tokens_total`, artificialanalysis→`intelligence_index`, aider→`pass_rate`, livebench→`average`, llmstats→`rating`. Descending, models missing the metric excluded.

- [ ] **Step 1: Write failing tests**

`tests/test_snapshot.py`:
```python
from modelwatch.registry import Registry
from modelwatch.snapshot import build_snapshot

REG = Registry([
    {"id": "a-model", "name": "A", "vendor": "V", "aliases": {"aider": ["a-raw"]}},
    {"id": "b-model", "name": "B", "vendor": "V", "aliases": {"aider": ["b-raw"]}},
])

def test_build_snapshot_scores_ranks_unmatched():
    results = {"aider": [
        {"raw_name": "a-raw", "metrics": {"pass_rate": 50.0}},
        {"raw_name": "b-raw", "metrics": {"pass_rate": 80.0}},
        {"raw_name": "mystery", "metrics": {"pass_rate": 99.0}},
    ]}
    snap, unmatched = build_snapshot(REG, results, prev=None, now_iso="2026-07-03T00:00:00Z")
    assert snap["models"]["a-model"]["scores"]["aider"]["pass_rate"] == 50.0
    assert snap["ranks"]["aider"] == ["b-model", "a-model"]
    assert unmatched == ["aider: mystery"]
    assert snap["sources"]["aider"]["ok"] is True

def test_failed_source_keeps_prev_data_and_marks_stale():
    prev = {"generated_at": "2026-07-02T00:00:00Z",
            "sources": {"aider": {"ok": True, "fetched_at": "2026-07-02T00:00:00Z", "stale_since": None}},
            "models": {"a-model": {"name": "A", "vendor": "V",
                                   "scores": {"aider": {"pass_rate": 50.0}}}},
            "ranks": {"aider": ["a-model"]}}
    snap, _ = build_snapshot(REG, {"aider": None}, prev=prev, now_iso="2026-07-03T00:00:00Z")
    assert snap["models"]["a-model"]["scores"]["aider"]["pass_rate"] == 50.0
    assert snap["sources"]["aider"]["ok"] is False
    assert snap["sources"]["aider"]["stale_since"] == "2026-07-02T00:00:00Z"
```

`tests/test_diff.py`:
```python
from modelwatch.diff import diff_snapshots

def _snap(models, ranks):
    return {"models": models, "ranks": ranks, "sources": {}}

def test_first_run_no_events():
    assert diff_snapshots(None, _snap({}, {})) == []

def test_new_model_and_rank_change():
    prev = _snap({"a": {"name": "A"}}, {"src": ["a"]})
    curr = _snap({"a": {"name": "A"}, "b": {"name": "B"}}, {"src": ["b", "a"]})
    events = diff_snapshots(prev, curr)
    types = {e["type"] for e in events}
    assert "new_model" in types
    rank = next(e for e in events if e["type"] == "rank_change")
    assert rank["model"] == "a" and rank["source"] == "src"
    assert rank["from"] == 1 and rank["to"] == 2
```

- [ ] **Step 2: Run, verify FAIL.**

- [ ] **Step 3: Implement**

`modelwatch/snapshot.py`:
```python
RANK_METRIC = {
    "openrouter": "tokens_total",
    "artificialanalysis": "intelligence_index",
    "aider": "pass_rate",
    "livebench": "average",
    "llmstats": "rating",
}


def build_snapshot(registry, results, prev, now_iso):
    prev = prev or {"models": {}, "sources": {}}
    models = {m["id"]: {"name": m["name"], "vendor": m["vendor"], "scores": {}}
              for m in registry.models}
    sources = {}
    unmatched = []

    for source_id, entries in results.items():
        if entries is None:  # fetch failed — carry last-good scores forward
            prev_src = prev["sources"].get(source_id, {})
            stale = prev_src.get("stale_since") or prev_src.get("fetched_at")
            sources[source_id] = {"ok": False,
                                  "fetched_at": prev_src.get("fetched_at"),
                                  "stale_since": stale}
            for mid, pm in prev["models"].items():
                if source_id in pm.get("scores", {}) and mid in models:
                    models[mid]["scores"][source_id] = pm["scores"][source_id]
            continue
        sources[source_id] = {"ok": True, "fetched_at": now_iso, "stale_since": None}
        for e in entries:
            mid = registry.canonical_id(source_id, e["raw_name"])
            if mid is None:
                unmatched.append(f"{source_id}: {e['raw_name']}")
                continue
            models[mid]["scores"][source_id] = e["metrics"]

    ranks = {}
    for source_id, metric in RANK_METRIC.items():
        scored = [(mid, m["scores"].get(source_id, {}).get(metric))
                  for mid, m in models.items()]
        scored = [(mid, v) for mid, v in scored if v is not None]
        ranks[source_id] = [mid for mid, _ in
                            sorted(scored, key=lambda t: t[1], reverse=True)]

    return ({"generated_at": now_iso, "sources": sources,
             "models": models, "ranks": ranks}, sorted(set(unmatched)))
```

`modelwatch/diff.py`:
```python
def diff_snapshots(prev, curr):
    if prev is None:
        return []
    events = []
    for mid, m in curr["models"].items():
        if mid not in prev["models"] and m.get("scores"):
            events.append({"type": "new_model", "model": mid, "name": m["name"]})
    for source_id, order in curr.get("ranks", {}).items():
        prev_order = prev.get("ranks", {}).get(source_id, [])
        prev_pos = {mid: i + 1 for i, mid in enumerate(prev_order)}
        for i, mid in enumerate(order):
            new_pos = i + 1
            if mid in prev_pos and prev_pos[mid] != new_pos:
                events.append({"type": "rank_change", "source": source_id,
                               "model": mid, "from": prev_pos[mid], "to": new_pos})
    for source_id, s in curr.get("sources", {}).items():
        prev_ok = prev.get("sources", {}).get(source_id, {}).get("ok", True)
        if prev_ok and s.get("ok") is False:
            events.append({"type": "source_stale", "source": source_id})
    return events
```

Note: `new_model` requires `m.get("scores")` non-empty — adding a not-yet-reported model to models.yaml shouldn't announce it.

- [ ] **Step 4: Run tests, verify PASS.**
- [ ] **Step 5: Commit** — `git commit -am "feat: snapshot builder and diff engine"`

---

### Task 7: Build orchestrator

**Files:**
- Create: `modelwatch/build.py`
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: all fetchers (`fetch()`), `build_snapshot`, `diff_snapshots`.
- Produces: `python -m modelwatch.build` writes `data/latest.json` (snapshot + `"changes"` key), `data/history/YYYY-MM-DD.json` (same content), `data/trends.json` (`{model_id: {source_id: {metric: [[date, value], ...]}}}` for the rank metrics only), `unmatched.txt`. `run(root: str, now: datetime) -> dict` for tests.

- [ ] **Step 1: Write failing test**

`tests/test_build.py`:
```python
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from modelwatch import build

def test_run_writes_outputs(tmp_path):
    (tmp_path / "models.yaml").write_text(
        "models:\n  - id: a-model\n    name: A\n    vendor: V\n"
        "    aliases: {aider: ['a-raw']}\n")
    fake_results = {"aider": [{"raw_name": "a-raw", "metrics": {"pass_rate": 50.0}}],
                    "openrouter": None, "artificialanalysis": None,
                    "livebench": None, "llmstats": None}
    with patch.object(build, "run_fetchers", return_value=fake_results):
        build.run(str(tmp_path), datetime(2026, 7, 3, tzinfo=timezone.utc))
    latest = json.loads((tmp_path / "data" / "latest.json").read_text())
    assert latest["models"]["a-model"]["scores"]["aider"]["pass_rate"] == 50.0
    assert latest["changes"] == []  # first run
    assert (tmp_path / "data" / "history" / "2026-07-03.json").exists()
    trends = json.loads((tmp_path / "data" / "trends.json").read_text())
    assert trends["a-model"]["aider"]["pass_rate"] == [["2026-07-03", 50.0]]
```

- [ ] **Step 2: Run, verify FAIL.**

- [ ] **Step 3: Implement**

`modelwatch/build.py`:
```python
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

from modelwatch.registry import load_registry
from modelwatch.snapshot import RANK_METRIC, build_snapshot
from modelwatch.diff import diff_snapshots
from modelwatch.fetchers import openrouter, artificialanalysis, aider, livebench, llmstats

FETCHERS = [openrouter, artificialanalysis, aider, livebench, llmstats]


def run_fetchers() -> dict:
    results = {}
    for mod in FETCHERS:
        try:
            results[mod.SOURCE_ID] = mod.fetch()
        except Exception:
            print(f"[warn] {mod.SOURCE_ID} fetch failed:\n{traceback.format_exc()}")
            results[mod.SOURCE_ID] = None
    return results


def _build_trends(history_dir: Path) -> dict:
    trends: dict = {}
    for f in sorted(history_dir.glob("*.json")):
        day = f.stem
        snap = json.loads(f.read_text(encoding="utf-8"))
        for mid, m in snap.get("models", {}).items():
            for source_id, metrics in m.get("scores", {}).items():
                metric = RANK_METRIC.get(source_id)
                v = metrics.get(metric) if metric else None
                if v is None:
                    continue
                trends.setdefault(mid, {}).setdefault(source_id, {}) \
                      .setdefault(metric, []).append([day, v])
    return trends


def run(root: str, now: datetime) -> dict:
    rootp = Path(root)
    data = rootp / "data"
    history = data / "history"
    history.mkdir(parents=True, exist_ok=True)

    prev = None
    latest_path = data / "latest.json"
    if latest_path.exists():
        prev = json.loads(latest_path.read_text(encoding="utf-8"))

    registry = load_registry(str(rootp / "models.yaml"))
    results = run_fetchers()
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    snap, unmatched = build_snapshot(registry, results, prev, now_iso)
    snap["changes"] = diff_snapshots(prev, snap)

    doc = json.dumps(snap, indent=1, ensure_ascii=False)
    latest_path.write_text(doc, encoding="utf-8")
    (history / f"{now.strftime('%Y-%m-%d')}.json").write_text(doc, encoding="utf-8")
    (data / "trends.json").write_text(
        json.dumps(_build_trends(history), ensure_ascii=False), encoding="utf-8")
    (rootp / "unmatched.txt").write_text("\n".join(unmatched), encoding="utf-8")
    print(f"sources ok: {[s for s, r in results.items() if r is not None]}; "
          f"unmatched: {len(unmatched)}")
    return snap


if __name__ == "__main__":
    run(".", datetime.now(timezone.utc))
```

- [ ] **Step 4: Run tests, verify PASS** (full suite: `.venv/Scripts/python.exe -m pytest -v`).
- [ ] **Step 5: Commit** — `git commit -am "feat: build orchestrator writing latest/history/trends"`

---

### Task 8: Site — HTML/CSS/JS + vendored Chart.js

**Files:**
- Create: `index.html`, `app.js`, `styles.css`, `vendor/chart.umd.js`, `data/sources.json` generation (small addition to build.py)

**Interfaces:**
- Consumes: `data/latest.json`, `data/trends.json`, `data/sources.json` (sources.yaml serialized — browsers can't read YAML natively).
- Produces: static dashboard with 4 sections: changes feed, model table (sortable), source cards by tier, charts (scatter intelligence-vs-blended-price + per-model sparklines).

- [ ] **Step 1: Extend build.py to emit `data/sources.json`**

Add to `run()` after registry load:
```python
import yaml  # top of file
sources_doc = yaml.safe_load((rootp / "sources.yaml").read_text(encoding="utf-8"))
(data / "sources.json").write_text(
    json.dumps(sources_doc, ensure_ascii=False), encoding="utf-8")
```
Add to `tests/test_build.py::test_run_writes_outputs`: write a minimal `sources.yaml` in tmp_path (`sources: []`) and assert `data/sources.json` exists. Run pytest → PASS. Commit: `git commit -am "feat: emit sources.json for site"`.

- [ ] **Step 2: Vendor Chart.js**

```bash
mkdir -p vendor
curl -L -o vendor/chart.umd.js https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.js
```

- [ ] **Step 3: Write `index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>model-watch</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<header>
  <h1>model-watch</h1>
  <p id="generated-at"></p>
</header>
<main>
  <section id="changes"><h2>What changed</h2><ul id="changes-list"></ul></section>
  <section id="table"><h2>Models</h2><div class="scroll"><table id="model-table"></table></div></section>
  <section id="charts">
    <h2>Charts</h2>
    <div class="chart-box"><canvas id="scatter"></canvas></div>
    <div id="sparklines"></div>
  </section>
  <section id="sources"><h2>Leaderboards</h2><div id="source-cards"></div></section>
</main>
<footer>
  Intelligence, speed &amp; price data by <a href="https://artificialanalysis.ai/">Artificial Analysis</a>.
  Usage data by <a href="https://openrouter.ai/rankings">OpenRouter</a>.
</footer>
<script src="vendor/chart.umd.js"></script>
<script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 4: Write `app.js`**

```javascript
async function loadJSON(p) { const r = await fetch(p); if (!r.ok) throw new Error(p); return r.json(); }

const METRIC_COLS = [
  ["artificialanalysis", "intelligence_index", "AA Intel"],
  ["artificialanalysis", "coding_index", "AA Coding"],
  ["livebench", "average", "LiveBench"],
  ["aider", "pass_rate", "Aider %"],
  ["llmstats", "rating", "llm-stats"],
  ["openrouter", "tokens_total", "OR usage"],
  ["artificialanalysis", "price_blended_per_1m", "$/1M blend"],
];

function fmt(v) {
  if (v == null) return "–";
  if (v >= 1e9) return (v / 1e9).toFixed(1) + "B";
  if (v >= 1e6) return (v / 1e6).toFixed(1) + "M";
  return typeof v === "number" ? +v.toFixed(2) : v;
}

function renderChanges(changes, models) {
  const ul = document.getElementById("changes-list");
  if (!changes.length) { ul.innerHTML = "<li>No changes since last build.</li>"; return; }
  for (const e of changes) {
    const li = document.createElement("li");
    const name = models[e.model]?.name ?? e.model;
    if (e.type === "new_model") li.textContent = `🆕 ${name} appeared`;
    else if (e.type === "rank_change")
      li.textContent = `${e.to < e.from ? "📈" : "📉"} ${name}: #${e.from} → #${e.to} on ${e.source}`;
    else if (e.type === "source_stale") li.textContent = `⚠️ ${e.source} fetch failing (stale data shown)`;
    ul.appendChild(li);
  }
}

function renderTable(latest) {
  const t = document.getElementById("model-table");
  const head = "<tr><th data-k='name'>Model</th><th>Vendor</th>" +
    METRIC_COLS.map((c, i) => `<th data-i="${i}">${c[2]}</th>`).join("") + "</tr>";
  const rows = Object.entries(latest.models)
    .filter(([, m]) => Object.keys(m.scores).length)
    .map(([id, m]) => ({ id, name: m.name, vendor: m.vendor,
      vals: METRIC_COLS.map(([s, k]) => m.scores[s]?.[k] ?? null) }));
  let sortI = 0, desc = true;
  function draw() {
    rows.sort((a, b) => ((b.vals[sortI] ?? -Infinity) - (a.vals[sortI] ?? -Infinity)) * (desc ? 1 : -1));
    t.innerHTML = head + rows.map(r =>
      `<tr><td>${r.name}</td><td>${r.vendor}</td>` +
      r.vals.map(v => `<td>${fmt(v)}</td>`).join("") + "</tr>").join("");
    t.querySelectorAll("th[data-i]").forEach(th =>
      th.onclick = () => { const i = +th.dataset.i; desc = i === sortI ? !desc : true; sortI = i; draw(); });
  }
  draw();
}

function renderSources(sourcesDoc, latest) {
  const box = document.getElementById("source-cards");
  const byTier = {};
  for (const s of sourcesDoc.sources) (byTier[s.tier] ??= []).push(s);
  for (const tier of Object.keys(byTier).sort()) {
    const h = document.createElement("h3");
    h.textContent = `Tier ${tier} — ${byTier[tier][0].tier_name}`;
    box.appendChild(h);
    const grid = document.createElement("div"); grid.className = "grid";
    for (const s of byTier[tier]) {
      const card = document.createElement("div"); card.className = "card";
      const status = latest.sources[s.id];
      let top = "";
      if (s.fetched && status) {
        const stale = status.ok ? "" : ` <span class="stale">stale since ${status.stale_since ?? "?"}</span>`;
        const top5 = (latest.ranks[s.id] || []).slice(0, 5)
          .map((mid, i) => `<li>${i + 1}. ${latest.models[mid]?.name ?? mid}</li>`).join("");
        top = `<ol class="top5">${top5}</ol><small>updated ${status.fetched_at ?? "?"}${stale}</small>`;
      }
      card.innerHTML = `<a href="${s.url}"><strong>${s.name}</strong></a>
        <p>${s.note ?? ""}</p>${top}`;
      grid.appendChild(card);
    }
    box.appendChild(grid);
  }
}

function renderCharts(latest, trends) {
  const pts = Object.entries(latest.models).map(([id, m]) => {
    const aa = m.scores.artificialanalysis;
    return aa?.intelligence_index != null && aa?.price_blended_per_1m != null
      ? { x: aa.price_blended_per_1m, y: aa.intelligence_index, label: m.name } : null;
  }).filter(Boolean);
  new Chart(document.getElementById("scatter"), {
    type: "scatter",
    data: { datasets: [{ label: "Intelligence vs $/1M (blended)", data: pts }] },
    options: { plugins: { tooltip: { callbacks: {
        label: c => `${c.raw.label}: ${c.raw.y} @ $${c.raw.x}/1M` } } },
      scales: { x: { title: { display: true, text: "$ per 1M tokens (blended)" }, type: "logarithmic" },
                y: { title: { display: true, text: "AA Intelligence Index" } } } },
  });
  const sp = document.getElementById("sparklines");
  for (const [mid, srcs] of Object.entries(trends)) {
    const series = srcs.artificialanalysis?.intelligence_index;
    if (!series || series.length < 2) continue;
    const wrap = document.createElement("div"); wrap.className = "spark";
    wrap.innerHTML = `<span>${latest.models[mid]?.name ?? mid}</span><canvas height="40"></canvas>`;
    sp.appendChild(wrap);
    new Chart(wrap.querySelector("canvas"), {
      type: "line",
      data: { labels: series.map(p => p[0]),
              datasets: [{ data: series.map(p => p[1]), pointRadius: 0, borderWidth: 1.5 }] },
      options: { plugins: { legend: { display: false } },
                 scales: { x: { display: false }, y: { display: false } } },
    });
  }
}

(async () => {
  const [latest, trends, sourcesDoc] = await Promise.all([
    loadJSON("data/latest.json"), loadJSON("data/trends.json"), loadJSON("data/sources.json")]);
  document.getElementById("generated-at").textContent = `Data as of ${latest.generated_at}`;
  renderChanges(latest.changes ?? [], latest.models);
  renderTable(latest);
  renderSources(sourcesDoc, latest);
  renderCharts(latest, trends);
})().catch(e => { document.body.insertAdjacentHTML("afterbegin",
  `<p class="error">Failed to load data: ${e.message}</p>`); });
```

- [ ] **Step 5: Write `styles.css`**

```css
:root { --bg: #0f1115; --fg: #e6e6e6; --muted: #9aa0a6; --card: #1a1d24; --accent: #6ab0f3; }
@media (prefers-color-scheme: light) {
  :root { --bg: #fafafa; --fg: #1a1a1a; --muted: #666; --card: #fff; --accent: #0b62c4; }
}
* { box-sizing: border-box; }
body { margin: 0 auto; max-width: 1100px; padding: 1rem; font: 15px/1.5 system-ui, sans-serif;
       background: var(--bg); color: var(--fg); }
a { color: var(--accent); }
h1 { margin-bottom: 0; } #generated-at { color: var(--muted); margin-top: .2rem; }
section { margin: 2rem 0; }
.scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; }
th, td { padding: .4rem .6rem; text-align: right; white-space: nowrap; }
th:first-child, td:first-child, th:nth-child(2), td:nth-child(2) { text-align: left; }
th { cursor: pointer; border-bottom: 2px solid var(--muted); }
tr:nth-child(even) { background: var(--card); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: .8rem; }
.card { background: var(--card); border-radius: 8px; padding: .8rem; }
.card p { color: var(--muted); font-size: .85rem; margin: .3rem 0; }
.top5 { margin: .3rem 0; padding-left: 1.2rem; font-size: .85rem; }
.stale { color: #e0a030; }
.chart-box { max-width: 700px; }
.spark { display: flex; align-items: center; gap: .6rem; max-width: 480px; }
.spark span { width: 160px; font-size: .85rem; }
#changes-list li { margin: .2rem 0; }
footer { color: var(--muted); font-size: .85rem; margin-top: 3rem; }
.error { background: #611; padding: .6rem; border-radius: 6px; }
```

- [ ] **Step 6: Smoke-test locally**

Run build with whatever sources work without keys (openrouter, aider, livebench succeed; AA/llm-stats fail-soft):
```bash
.venv/Scripts/python.exe -m modelwatch.build
.venv/Scripts/python.exe -m http.server 8000
```
Open http://localhost:8000 — verify: table renders keyless-source columns, source cards show top-5s + tiers, changes feed says "No changes", no console errors (charts section may be sparse without AA data — acceptable).

- [ ] **Step 7: Commit** — `git add -A && git commit -m "feat: dashboard site (table, cards, changes feed, charts)"`

---

### Task 9: Live-run correction loop (keys, aliases, llm-stats payload)

**Files:**
- Modify: `models.yaml` (aliases), possibly `modelwatch/fetchers/llmstats.py` + its test

**Interfaces:**
- Consumes: everything. Manual inputs from Richard: `ARTIFICIALANALYSIS_API_KEY` (signup via artificialanalysis.ai Insights account), `LLMSTATS_API_KEY` (https://llm-stats.com/settings?tab=api-keys).

- [ ] **Step 1: Ask Richard for the two API keys** (blocker — pause here if not available; sources fail-soft meanwhile).
- [ ] **Step 2: Full live run** — `ARTIFICIALANALYSIS_API_KEY=... LLMSTATS_API_KEY=... .venv/Scripts/python.exe -m modelwatch.build`. All 5 sources must report ok.
- [ ] **Step 3: Fix llm-stats parser against real payload** — inspect real `/v1/rankings` response; update `llmstats.parse` field mapping + sample in `tests/test_fetch_parsers.py` to the actual shape. Re-run pytest → PASS.
- [ ] **Step 4: Alias pass** — read `unmatched.txt`; for every frontier model in the shortlist, add per-source alias entries to `models.yaml` until each shortlist model matches in every source that covers it. Also extend shortlist with any current frontier models the feeds reveal that Richard's list missed (judgment call, keep ~15-25).
- [ ] **Step 5: Re-run build + local smoke test** — table now has AA/llm-stats columns populated; scatter chart renders.
- [ ] **Step 6: Commit** — `git add -A && git commit -m "feat: live-verified aliases and llmstats payload mapping"` (data/ files included — they're the site's content).

---

### Task 10: GitHub repo, Action, Pages

**Files:**
- Create: `.github/workflows/build.yml`

**Interfaces:**
- Consumes: `python -m modelwatch.build`. Secrets `ARTIFICIALANALYSIS_API_KEY`, `LLMSTATS_API_KEY` in repo Actions secrets.

- [ ] **Step 1: Write workflow**

`.github/workflows/build.yml`:
```yaml
name: build
on:
  schedule:
    - cron: "20 6 * * *"   # daily 06:20 UTC
  workflow_dispatch:
permissions:
  contents: write
concurrency: build
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt
      - run: python -m pytest
      - run: python -m modelwatch.build
        env:
          ARTIFICIALANALYSIS_API_KEY: ${{ secrets.ARTIFICIALANALYSIS_API_KEY }}
          LLMSTATS_API_KEY: ${{ secrets.LLMSTATS_API_KEY }}
      - uses: actions/upload-artifact@v4
        with: { name: unmatched, path: unmatched.txt, if-no-files-found: ignore }
      - name: Commit data
        run: |
          git config user.name "model-watch-bot"
          git config user.email "actions@users.noreply.github.com"
          git add data/
          git diff --cached --quiet || git commit -m "chore: daily data refresh"
          git push
```

- [ ] **Step 2: Create GitHub repo + push**

```bash
gh repo create richardadonnell/model-watch --public --source . --push
gh secret set ARTIFICIALANALYSIS_API_KEY --repo richardadonnell/model-watch
gh secret set LLMSTATS_API_KEY --repo richardadonnell/model-watch
```

- [ ] **Step 3: Enable Pages** (main branch, root):

```bash
gh api -X POST repos/richardadonnell/model-watch/pages -f "source[branch]=main" -f "source[path]=/"
```
(If 409 already exists, fine. If API shape rejected, enable in repo Settings → Pages UI.)

- [ ] **Step 4: Trigger + verify**

```bash
gh workflow run build --repo richardadonnell/model-watch
gh run watch --repo richardadonnell/model-watch
```
Expected: green run, data commit pushed. Then open `https://richardadonnell.github.io/model-watch/` — dashboard renders with live data.

- [ ] **Step 5: Move spec + plan into new repo's `docs/`, commit** — copy `2026-07-03-model-watch-design.md` and this plan from personal-assistant into `model-watch/docs/`, commit `docs: import design spec and plan`.

---

## Self-review notes

- Spec coverage: pipeline (T4-7), site 4 views (T8), infra (T10), error handling (T6 stale logic, T7 fail-soft, app.js error banner), testing (T2-7), launchpad 24-site list (T3), attribution (T8 footer + README). HF dropped per research (frozen) — reflected in T3 note.
- Known softness, deliberate: llm-stats payload shape unverified until Task 9 (explicitly planned correction step); models.yaml seed slugs corrected by unmatched-log loop. Not placeholders — planned verification steps with exact procedure.
