import csv
import io

import requests

SOURCE_ID = "epoch"
# Epoch AI Benchmarking Hub per-run results feed (CC BY 4.0, attribution
# required — see the site footer link). One row per eval run.
CSV_URL = "https://epoch.ai/data/benchmarks.csv"

# Benchmarks tracked, chosen for broadest current-frontier coverage:
# task name in the CSV -> snake_case metric key (scores scaled 0-100).
TRACKED_TASKS = {
    "GPQA diamond": "gpqa_diamond_pct",
    "OTIS Mock AIME 2024-2025": "otis_mock_aime_pct",
    "SWE-Bench verified": "swe_bench_verified_pct",
}


def parse(csv_text: str) -> dict:
    """Aggregate per-run rows into one entry per model.

    Returns {"entries": [...], "data_date": str|None} where each entry
    carries the mean score per tracked benchmark scaled to 0-100, and
    data_date is the latest run start date (YYYY-MM-DD) across all rows.
    """
    # scores[model][metric_key] = list of run scores (0-1 fractions)
    scores: dict[str, dict[str, list[float]]] = {}
    max_date = None
    for row in csv.DictReader(io.StringIO(csv_text)):
        started = (row.get("started_at") or "")[:10]
        if len(started) == 10 and (max_date is None or started > max_date):
            max_date = started
        key = TRACKED_TASKS.get(row.get("task") or "")
        name = row.get("model")
        if not key or not name:
            continue
        try:
            score = float(row.get("mean_score") or "")
        except ValueError:
            continue  # empty or non-numeric score cell
        scores.setdefault(name, {}).setdefault(key, []).append(score)

    entries = []
    for name, per_task in scores.items():
        metrics = {
            key: round(100 * sum(vals) / len(vals), 1)
            for key, vals in per_task.items()
        }
        entries.append({"raw_name": name, "metrics": metrics})
    return {"entries": entries, "data_date": max_date}


def fetch() -> dict:
    r = requests.get(CSV_URL, timeout=60)
    r.raise_for_status()
    return parse(r.text)
