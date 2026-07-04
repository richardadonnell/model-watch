import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

import yaml

from modelwatch.registry import load_registry
from modelwatch.snapshot import RANK_METRIC, build_snapshot
from modelwatch.diff import diff_snapshots
from modelwatch.suggest import build_suggestions
from modelwatch.fetchers import (
    openrouter,
    artificialanalysis,
    livebench,
)

FETCHERS = [openrouter, artificialanalysis, livebench]


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
        try:
            snap = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            print(f"[warn] skipping unreadable history file: {f}")
            continue
        for mid, m in snap.get("models", {}).items():
            for source_id, metrics in m.get("scores", {}).items():
                metric = RANK_METRIC.get(source_id)
                v = metrics.get(metric) if metric else None
                if v is None:
                    continue
                trends.setdefault(mid, {}).setdefault(source_id, {}).setdefault(
                    metric, []
                ).append([day, v])
    return trends


def run(root: str, now: datetime) -> dict:
    rootp = Path(root)
    data = rootp / "data"
    history = data / "history"
    history.mkdir(parents=True, exist_ok=True)

    prev = None
    latest_path = data / "latest.json"
    if latest_path.exists():
        try:
            prev = json.loads(latest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            print(
                f"[warn] unreadable latest.json, treating as first run: {latest_path}"
            )
            prev = None

    registry = load_registry(str(rootp / "models.yaml"))
    sources_doc = yaml.safe_load((rootp / "sources.yaml").read_text(encoding="utf-8"))
    (data / "sources.json").write_text(
        json.dumps(sources_doc, ensure_ascii=False), encoding="utf-8"
    )
    results = run_fetchers()
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    snap, unmatched = build_snapshot(registry, results, prev, now_iso)
    snap["changes"] = diff_snapshots(prev, snap)

    doc = json.dumps(snap, indent=1, ensure_ascii=False)
    # History is the durable record; latest.json is derivable from it, so write
    # history first — if the process dies mid-write, we don't lose the day's record.
    (history / f"{now.strftime('%Y-%m-%d')}.json").write_text(doc, encoding="utf-8")
    latest_path.write_text(doc, encoding="utf-8")
    (data / "trends.json").write_text(
        json.dumps(_build_trends(history), ensure_ascii=False), encoding="utf-8"
    )
    (data / "suggestions.json").write_text(
        json.dumps(build_suggestions(registry, results), ensure_ascii=False),
        encoding="utf-8",
    )
    (rootp / "unmatched.txt").write_text("\n".join(unmatched), encoding="utf-8")
    print(
        f"sources ok: {[s for s, r in results.items() if r is not None]}; "
        f"unmatched: {len(unmatched)}"
    )
    return snap


if __name__ == "__main__":
    run(".", datetime.now(timezone.utc))
