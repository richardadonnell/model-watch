from modelwatch.diff import diff_snapshots


def _snap(models, ranks):
    return {"models": models, "ranks": ranks, "sources": {}}


def test_first_run_no_events():
    assert diff_snapshots(None, _snap({}, {})) == []


def test_new_model_and_rank_change():
    prev = _snap({"a": {"name": "A"}}, {"src": ["a"]})
    curr = _snap(
        {"a": {"name": "A"}, "b": {"name": "B", "scores": {"src": {}}}},
        {"src": ["b", "a"]},
    )
    events = diff_snapshots(prev, curr)
    types = {e["type"] for e in events}
    assert "new_model" in types
    rank = next(e for e in events if e["type"] == "rank_change")
    assert rank["model"] == "a" and rank["source"] == "src"
    assert rank["from"] == 1 and rank["to"] == 2
