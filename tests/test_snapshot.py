from modelwatch.registry import Registry
from modelwatch.snapshot import build_snapshot

REG = Registry(
    [
        {"id": "a-model", "name": "A", "vendor": "V", "aliases": {"livebench": ["a-raw"]}},
        {"id": "b-model", "name": "B", "vendor": "V", "aliases": {"livebench": ["b-raw"]}},
    ]
)


def test_build_snapshot_scores_ranks_unmatched():
    results = {
        "livebench": {
            "entries": [
                {"raw_name": "a-raw", "metrics": {"average": 50.0}},
                {"raw_name": "b-raw", "metrics": {"average": 80.0}},
                {"raw_name": "mystery", "metrics": {"average": 99.0}},
            ],
            "data_date": "2026-06-01",
        }
    }
    snap, unmatched = build_snapshot(
        REG, results, prev=None, now_iso="2026-07-03T00:00:00Z"
    )
    assert snap["models"]["a-model"]["scores"]["livebench"]["average"] == 50.0
    assert snap["ranks"]["livebench"] == ["b-model", "a-model"]
    assert unmatched == ["livebench: mystery"]
    assert snap["sources"]["livebench"]["ok"] is True
    assert snap["sources"]["livebench"]["data_date"] == "2026-06-01"


def test_failed_source_keeps_prev_data_and_marks_stale():
    prev = {
        "generated_at": "2026-07-02T00:00:00Z",
        "sources": {
            "livebench": {
                "ok": True,
                "fetched_at": "2026-07-02T00:00:00Z",
                "stale_since": None,
            }
        },
        "models": {
            "a-model": {
                "name": "A",
                "vendor": "V",
                "scores": {"livebench": {"average": 50.0}},
            }
        },
        "ranks": {"livebench": ["a-model"]},
    }
    snap, _ = build_snapshot(
        REG, {"livebench": None}, prev=prev, now_iso="2026-07-03T00:00:00Z"
    )
    assert snap["models"]["a-model"]["scores"]["livebench"]["average"] == 50.0
    assert snap["sources"]["livebench"]["ok"] is False
    assert snap["sources"]["livebench"]["stale_since"] == "2026-07-02T00:00:00Z"
