PRICE_CHANGE_PCT = 0.05  # emit price_change only on a >=5% relative move


def diff_snapshots(prev, curr):
    if prev is None:
        return []
    events = []
    for mid, m in curr["models"].items():
        if mid not in prev["models"] and m.get("scores"):
            events.append({"type": "new_model", "model": mid, "name": m["name"]})

    for mid, m in curr["models"].items():
        if mid not in prev["models"]:
            continue
        new_p = m.get("scores", {}).get("openrouter", {}).get("price_out_per_1m")
        old_p = (
            prev["models"][mid]
            .get("scores", {})
            .get("openrouter", {})
            .get("price_out_per_1m")
        )
        if not old_p or not new_p:  # skip missing/None/zero
            continue
        if abs(new_p - old_p) / old_p >= PRICE_CHANGE_PCT:
            events.append(
                {"type": "price_change", "model": mid, "from": old_p, "to": new_p}
            )
    for source_id, order in curr.get("ranks", {}).items():
        prev_order = prev.get("ranks", {}).get(source_id, [])
        shared = set(prev_order) & set(order)
        prev_shared = [mid for mid in prev_order if mid in shared]
        curr_shared = [mid for mid in order if mid in shared]
        prev_pos = {mid: i + 1 for i, mid in enumerate(prev_shared)}
        for i, mid in enumerate(curr_shared):
            new_pos = i + 1
            if prev_pos[mid] != new_pos:
                events.append(
                    {
                        "type": "rank_change",
                        "source": source_id,
                        "model": mid,
                        "from": prev_pos[mid],
                        "to": new_pos,
                    }
                )
    prev_sources = prev.get("sources", {})
    for source_id, s in curr.get("sources", {}).items():
        # Only a source that previously succeeded can go stale. A source with
        # no prior entry has no data to lose, so its first-ever failure is not
        # a staleness event.
        if source_id in prev_sources and prev_sources[source_id].get("ok") is True:
            if s.get("ok") is False:
                events.append({"type": "source_stale", "source": source_id})
    return events
