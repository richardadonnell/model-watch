RANK_METRIC = {
    "openrouter": "tokens_total",
    "artificialanalysis": "intelligence_index",
    "livebench": "average",
}


def build_snapshot(registry, results, prev, now_iso):
    prev = prev or {"models": {}, "sources": {}}
    models = {
        m["id"]: {"name": m["name"], "vendor": m["vendor"], "scores": {}}
        for m in registry.models
    }
    sources = {}
    unmatched = []

    for source_id, result in results.items():
        if result is None:  # fetch failed — carry last-good scores forward
            prev_src = prev["sources"].get(source_id, {})
            stale = prev_src.get("stale_since") or prev_src.get("fetched_at")
            sources[source_id] = {
                "ok": False,
                "fetched_at": prev_src.get("fetched_at"),
                "stale_since": stale,
                "data_date": prev_src.get("data_date"),
            }
            for mid, pm in prev["models"].items():
                if source_id in pm.get("scores", {}) and mid in models:
                    models[mid]["scores"][source_id] = pm["scores"][source_id]
            continue
        sources[source_id] = {
            "ok": True,
            "fetched_at": now_iso,
            "stale_since": None,
            "data_date": result.get("data_date"),
        }
        for e in result["entries"]:
            mid = registry.canonical_id(source_id, e["raw_name"])
            if mid is None:
                unmatched.append(f"{source_id}: {e['raw_name']}")
                continue
            models[mid]["scores"][source_id] = e["metrics"]

    ranks = {}
    for source_id, metric in RANK_METRIC.items():
        scored = [
            (mid, m["scores"].get(source_id, {}).get(metric))
            for mid, m in models.items()
        ]
        scored = [(mid, v) for mid, v in scored if v is not None]
        ranks[source_id] = [
            mid for mid, _ in sorted(scored, key=lambda t: t[1], reverse=True)
        ]

    return (
        {"generated_at": now_iso, "sources": sources, "models": models, "ranks": ranks},
        sorted(set(unmatched)),
    )
