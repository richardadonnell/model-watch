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
    # "a" is the only model shared between prev and curr; its relative
    # order among shared models is unchanged (still position 1), so no
    # rank_change should be emitted even though its absolute index shifted.
    assert "rank_change" not in types


def test_new_model_does_not_trigger_rank_change():
    prev = _snap(
        {"a": {"name": "A"}, "b": {"name": "B"}, "c": {"name": "C"}},
        {"src": ["a", "b", "c"]},
    )
    curr = _snap(
        {
            "a": {"name": "A"},
            "b": {"name": "B"},
            "c": {"name": "C"},
            "new": {"name": "New", "scores": {"src": {}}},
        },
        {"src": ["new", "a", "b", "c"]},
    )
    events = diff_snapshots(prev, curr)
    types = {e["type"] for e in events}
    assert "new_model" in types
    assert "rank_change" not in types


def test_rank_change_relative_order_swap():
    prev = _snap({"a": {"name": "A"}, "b": {"name": "B"}}, {"src": ["a", "b"]})
    curr = _snap({"a": {"name": "A"}, "b": {"name": "B"}}, {"src": ["b", "a"]})
    events = diff_snapshots(prev, curr)
    rank_events = [e for e in events if e["type"] == "rank_change"]
    assert len(rank_events) == 2
    by_model = {e["model"]: e for e in rank_events}
    assert by_model["a"]["from"] == 1 and by_model["a"]["to"] == 2
    assert by_model["b"]["from"] == 2 and by_model["b"]["to"] == 1
