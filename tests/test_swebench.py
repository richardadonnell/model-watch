from modelwatch.fetchers import swebench

SB = {
    "leaderboards": [
        {
            "name": "Verified",
            "results": [
                {"name": "SomeAgent + Claude", "resolved": 79.2, "date": "2026-03-01"}
            ],
        },
        {
            "name": "bash-only",
            "results": [
                {
                    "name": "Claude 4.5 Opus (high reasoning)",
                    "resolved": 76.8,
                    "instance_cost": 0.753907997,
                    "date": "2026-02-17",
                },
                {
                    "name": "Gemini 3 Pro",
                    "resolved": 69.6,
                    "instance_cost": 0.9600198564,
                    "date": "2026-02-26",
                },
                {
                    # No top-level "resolved": derived from per-instance details.
                    "name": "Devstral small (2512)",
                    "instance_cost": None,
                    "date": "2025-12-09",
                    "per_instance_details": {
                        "a__b-1": {"resolved": True},
                        "a__b-2": {"resolved": False},
                        "a__b-3": {"resolved": True},
                        "a__b-4": {"resolved": True},
                    },
                },
                {
                    # No score at all -> dropped, not crashed.
                    "name": "Broken Entry",
                    "date": "2026-09-09",
                },
            ],
        },
    ]
}


def test_swebench_parse_picks_bash_only_split():
    out = swebench.parse(SB)
    names = [e["raw_name"] for e in out["entries"]]
    assert "Claude 4.5 Opus (high reasoning)" in names
    # Verified-split entries must not leak in.
    assert "SomeAgent + Claude" not in names


def test_swebench_parse_metrics():
    out = swebench.parse(SB)
    row = next(
        e
        for e in out["entries"]
        if e["raw_name"] == "Claude 4.5 Opus (high reasoning)"
    )
    assert row["metrics"]["resolved_pct"] == 76.8
    assert row["metrics"]["cost_per_instance"] == 0.7539


def test_swebench_parse_derives_resolved_from_per_instance_details():
    out = swebench.parse(SB)
    row = next(e for e in out["entries"] if e["raw_name"] == "Devstral small (2512)")
    assert row["metrics"]["resolved_pct"] == 75.0  # 3 of 4 resolved
    # Null instance_cost must not emit a cost metric.
    assert "cost_per_instance" not in row["metrics"]


def test_swebench_parse_drops_scoreless_entries():
    out = swebench.parse(SB)
    names = [e["raw_name"] for e in out["entries"]]
    assert "Broken Entry" not in names
    # And its date must not pollute data_date.
    assert out["data_date"] == "2026-02-26"


def test_swebench_parse_data_date_is_max_entry_date():
    assert swebench.parse(SB)["data_date"] == "2026-02-26"


def test_swebench_parse_empty_and_malformed_payloads():
    assert swebench.parse({}) == {"entries": [], "data_date": None}
    assert swebench.parse({"leaderboards": []}) == {"entries": [], "data_date": None}
    assert swebench.parse({"leaderboards": [{"name": "bash-only"}]}) == {
        "entries": [],
        "data_date": None,
    }
