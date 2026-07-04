from modelwatch.suggest import build_suggestions


class FakeRegistry:
    """Stub registry: knows canonical ids only for (source_id, raw_name) pairs
    in `known`; everything else is unknown (returns None)."""

    def __init__(self, known):
        self.known = known

    def canonical_id(self, source_id, raw_name):
        return self.known.get((source_id, raw_name))


def test_returns_unknown_candidates_ranked_by_metric():
    reg = FakeRegistry({("artificialanalysis", "known-model"): "known-id"})
    results = {
        "artificialanalysis": {
            "entries": [
                {"raw_name": "known-model", "metrics": {"intelligence_index": 90.0}},
                {"raw_name": "new-low", "metrics": {"intelligence_index": 60.0}},
                {"raw_name": "new-high", "metrics": {"intelligence_index": 80.0}},
            ],
        }
    }
    out = build_suggestions(reg, results)
    assert [s["raw_name"] for s in out] == ["new-high", "new-low"]
    assert all(s["source"] == "artificialanalysis" for s in out)
    assert out[0] == {
        "source": "artificialanalysis",
        "raw_name": "new-high",
        "metric": "intelligence_index",
        "value": 80.0,
    }


def test_none_source_is_skipped():
    reg = FakeRegistry({})
    results = {"artificialanalysis": None}
    assert build_suggestions(reg, results) == []


def test_candidate_missing_metric_is_dropped():
    reg = FakeRegistry({})
    results = {
        "livebench": {
            "entries": [
                {"raw_name": "has-metric", "metrics": {"average": 70.0}},
                {"raw_name": "no-metric-key", "metrics": {}},
                {"raw_name": "none-metric", "metrics": {"average": None}},
            ],
        }
    }
    out = build_suggestions(reg, results)
    assert [s["raw_name"] for s in out] == ["has-metric"]


def test_top_k_truncates():
    reg = FakeRegistry({})
    results = {
        "livebench": {
            "entries": [
                {"raw_name": f"m{i}", "metrics": {"average": float(i)}}
                for i in range(5)
            ],
        }
    }
    out = build_suggestions(reg, results, top_k=2)
    assert [s["raw_name"] for s in out] == ["m4", "m3"]
