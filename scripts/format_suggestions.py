"""Render data/suggestions.json into a markdown GitHub-issue body.

Usage: python scripts/format_suggestions.py data/suggestions.json > body.md
Stdlib only — safe to run in CI without installing project deps.
"""

import json
import sys
from collections import OrderedDict

_HEADER = (
    "These are high-signal models that appear near the top of one or more "
    "leaderboards but are **missing from `models.yaml`** (the shortlist).\n\n"
    "To add one: add its canonical `id` (plus `name`/`vendor`) to `models.yaml`, "
    "and give it a per-source alias entry under `aliases:` matching the "
    "`raw_name` shown below so the fetcher can match it.\n"
)

_EMPTY = (
    "No new model suggestions right now — every strong model on the tracked "
    "leaderboards is already in `models.yaml`.\n"
)


def format_body(suggestions: list[dict]) -> str:
    if not suggestions:
        return _EMPTY

    by_source: "OrderedDict[str, list[dict]]" = OrderedDict()
    for s in suggestions:
        by_source.setdefault(s["source"], []).append(s)

    parts = [_HEADER]
    for source, items in by_source.items():
        parts.append(f"\n## {source}\n")
        parts.append("| raw_name | metric | value |")
        parts.append("| --- | --- | --- |")
        for it in items:
            parts.append(f"| {it['raw_name']} | {it['metric']} | {it['value']} |")
        parts.append("")
    return "\n".join(parts) + "\n"


def main(argv: list[str]) -> int:
    path = argv[1]
    with open(path, encoding="utf-8") as f:
        suggestions = json.load(f)
    sys.stdout.write(format_body(suggestions))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
