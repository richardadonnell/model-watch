import requests

SOURCE_ID = "swebench"
LEADERBOARDS_URL = (
    "https://raw.githubusercontent.com/SWE-bench/swe-bench.github.io"
    "/master/data/leaderboards.json"
)
# The "bash-only" split is the mini-swe-agent model-only leaderboard: every
# entry is the same minimal scaffold, so scores compare *models* directly
# (unlike "Verified", which mixes heavyweight agent scaffolds). It also
# carries the freshest frontier models and per-instance cost.
SPLIT = "bash-only"


def parse(payload: dict) -> dict:
    """Pure parser: leaderboards.json payload -> {"entries", "data_date"}."""
    entries: list[dict] = []
    max_date: str | None = None
    boards = payload.get("leaderboards") if isinstance(payload, dict) else None
    results = next(
        (
            lb.get("results") or []
            for lb in (boards or [])
            if isinstance(lb, dict) and lb.get("name") == SPLIT
        ),
        [],
    )
    for r in results:
        if not isinstance(r, dict) or not r.get("name"):
            continue
        resolved = r.get("resolved")
        # bash-only entries may omit "resolved"; derive from per-instance
        # details when possible so those rows aren't silently dropped.
        if resolved is None:
            details = r.get("per_instance_details")
            if isinstance(details, dict) and details:
                n_ok = sum(1 for v in details.values() if v.get("resolved"))
                resolved = round(100.0 * n_ok / len(details), 2)
        if resolved is None:
            continue
        metrics = {"resolved_pct": float(resolved)}
        cost = r.get("instance_cost")
        if cost is not None:
            metrics["cost_per_instance"] = round(float(cost), 4)
        entries.append({"raw_name": r["name"], "metrics": metrics})
        date = r.get("date")
        if date and (max_date is None or date > max_date):
            max_date = date
    return {"entries": entries, "data_date": max_date}


def fetch() -> dict:
    r = requests.get(LEADERBOARDS_URL, timeout=60)
    r.raise_for_status()
    return parse(r.json())
