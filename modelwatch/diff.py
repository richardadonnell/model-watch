def diff_snapshots(prev, curr):
    if prev is None:
        return []
    events = []
    for mid, m in curr["models"].items():
        if mid not in prev["models"] and m.get("scores"):
            events.append({"type": "new_model", "model": mid, "name": m["name"]})
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
    for source_id, s in curr.get("sources", {}).items():
        prev_ok = prev.get("sources", {}).get(source_id, {}).get("ok", True)
        if prev_ok and s.get("ok") is False:
            events.append({"type": "source_stale", "source": source_id})
    return events
