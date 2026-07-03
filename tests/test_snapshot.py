from modelwatch.registry import Registry
from modelwatch.snapshot import build_snapshot

REG = Registry(
    [
        {"id": "a-model", "name": "A", "vendor": "V", "aliases": {"aider": ["a-raw"]}},
        {"id": "b-model", "name": "B", "vendor": "V", "aliases": {"aider": ["b-raw"]}},
    ]
)


def test_build_snapshot_scores_ranks_unmatched():
    results = {
        "aider": [
            {"raw_name": "a-raw", "metrics": {"pass_rate": 50.0}},
            {"raw_name": "b-raw", "metrics": {"pass_rate": 80.0}},
            {"raw_name": "mystery", "metrics": {"pass_rate": 99.0}},
        ]
    }
    snap, unmatched = build_snapshot(
        REG, results, prev=None, now_iso="2026-07-03T00:00:00Z"
    )
    assert snap["models"]["a-model"]["scores"]["aider"]["pass_rate"] == 50.0
    assert snap["ranks"]["aider"] == ["b-model", "a-model"]
    assert unmatched == ["aider: mystery"]
    assert snap["sources"]["aider"]["ok"] is True


def test_failed_source_keeps_prev_data_and_marks_stale():
    prev = {
        "generated_at": "2026-07-02T00:00:00Z",
        "sources": {
            "aider": {
                "ok": True,
                "fetched_at": "2026-07-02T00:00:00Z",
                "stale_since": None,
            }
        },
        "models": {
            "a-model": {
                "name": "A",
                "vendor": "V",
                "scores": {"aider": {"pass_rate": 50.0}},
            }
        },
        "ranks": {"aider": ["a-model"]},
    }
    snap, _ = build_snapshot(
        REG, {"aider": None}, prev=prev, now_iso="2026-07-03T00:00:00Z"
    )
    assert snap["models"]["a-model"]["scores"]["aider"]["pass_rate"] == 50.0
    assert snap["sources"]["aider"]["ok"] is False
    assert snap["sources"]["aider"]["stale_since"] == "2026-07-02T00:00:00Z"
