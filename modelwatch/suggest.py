from modelwatch.snapshot import RANK_METRIC


def build_suggestions(registry, results, top_k=10) -> list[dict]:
    """Surface strong models present in fetched sources but missing from the
    shortlist (models.yaml). A candidate is an entry whose canonical_id is None.

    Candidates are ranked within each source by that source's RANK_METRIC,
    descending; entries with a missing/None metric value are dropped. Returns a
    flat list ordered source-by-source (in `results` dict order)."""
    suggestions: list[dict] = []
    for source_id, result in results.items():
        if result is None:
            continue
        metric = RANK_METRIC.get(source_id)
        if metric is None:
            continue
        candidates = []
        for e in result["entries"]:
            if registry.canonical_id(source_id, e["raw_name"]) is not None:
                continue
            value = e.get("metrics", {}).get(metric)
            if value is None:
                continue
            candidates.append((e["raw_name"], value))
        candidates.sort(key=lambda t: t[1], reverse=True)
        for raw_name, value in candidates[:top_k]:
            suggestions.append(
                {
                    "source": source_id,
                    "raw_name": raw_name,
                    "metric": metric,
                    "value": value,
                }
            )
    return suggestions
