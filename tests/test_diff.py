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


def test_source_stale_not_emitted_for_never_succeeded_source():
    # prev has no entry for source 'x' -> its first-ever failure is not "stale".
    prev = {"models": {}, "ranks": {}, "sources": {}}
    curr = {"models": {}, "ranks": {}, "sources": {"x": {"ok": False}}}
    events = diff_snapshots(prev, curr)
    assert not any(e["type"] == "source_stale" for e in events)


def test_source_stale_emitted_when_previously_ok():
    prev = {"models": {}, "ranks": {}, "sources": {"x": {"ok": True}}}
    curr = {"models": {}, "ranks": {}, "sources": {"x": {"ok": False}}}
    events = diff_snapshots(prev, curr)
    assert any(e["type"] == "source_stale" and e["source"] == "x" for e in events)


def _snap_scored(models):
    return {"models": models, "ranks": {}, "sources": {}}


def test_price_change_emitted_above_threshold():
    prev = _snap_scored(
        {"a": {"name": "A", "scores": {"openrouter": {"price_out_per_1m": 10.0}}}}
    )
    curr = _snap_scored(
        {"a": {"name": "A", "scores": {"openrouter": {"price_out_per_1m": 12.0}}}}
    )
    events = diff_snapshots(prev, curr)
    pc = [e for e in events if e["type"] == "price_change"]
    assert len(pc) == 1
    assert pc[0]["model"] == "a" and pc[0]["from"] == 10.0 and pc[0]["to"] == 12.0


def test_price_change_ignored_below_threshold():
    prev = _snap_scored(
        {"a": {"name": "A", "scores": {"openrouter": {"price_out_per_1m": 10.0}}}}
    )
    curr = _snap_scored(
        {"a": {"name": "A", "scores": {"openrouter": {"price_out_per_1m": 10.2}}}}
    )
    events = diff_snapshots(prev, curr)
    assert not any(e["type"] == "price_change" for e in events)


def test_price_change_no_crash_on_missing_price():
    prev = _snap_scored(
        {"a": {"name": "A", "scores": {"openrouter": {"price_out_per_1m": None}}}}
    )
    curr = _snap_scored({"a": {"name": "A", "scores": {"openrouter": {}}}})
    events = diff_snapshots(prev, curr)
    assert not any(e["type"] == "price_change" for e in events)


def test_rank_change_relative_order_swap():
    prev = _snap({"a": {"name": "A"}, "b": {"name": "B"}}, {"src": ["a", "b"]})
    curr = _snap({"a": {"name": "A"}, "b": {"name": "B"}}, {"src": ["b", "a"]})
    events = diff_snapshots(prev, curr)
    rank_events = [e for e in events if e["type"] == "rank_change"]
    assert len(rank_events) == 2
    by_model = {e["model"]: e for e in rank_events}
    assert by_model["a"]["from"] == 1 and by_model["a"]["to"] == 2
    assert by_model["b"]["from"] == 2 and by_model["b"]["to"] == 1
