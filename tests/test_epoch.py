from modelwatch.fetchers import epoch

HEADER = "id_runs,task,model,started_at,mean_score,best_score\n"

EPOCH_CSV = HEADER + (
    # Two GPQA runs for the same model -> averaged.
    "r1,GPQA diamond,claude-fable-5_max,2026-06-01T10:00:00.000Z,0.90,0.90\n"
    "r2,GPQA diamond,claude-fable-5_max,2026-06-25T13:13:06.902Z,0.80,0.81\n"
    # A second tracked benchmark for the same model.
    "r3,SWE-Bench verified,claude-fable-5_max,2026-05-05T00:00:00.000Z,0.787,0.787\n"
    # Untracked benchmark -> ignored entirely.
    "r4,Chess Puzzles,claude-fable-5_max,2026-06-30T00:00:00.000Z,0.5,0.5\n"
    # Different model, one tracked run.
    "r5,OTIS Mock AIME 2024-2025,glm-5.2_max,2026-06-10T00:00:00.000Z,0.8639,0.9\n"
)


def test_epoch_parse_aggregates_mean_per_model_per_benchmark():
    out = epoch.parse(EPOCH_CSV)
    entry = next(e for e in out["entries"] if e["raw_name"] == "claude-fable-5_max")
    # (0.90 + 0.80) / 2 = 0.85 -> 85.0 on the 0-100 scale
    assert entry["metrics"]["gpqa_diamond_pct"] == 85.0
    assert entry["metrics"]["swe_bench_verified_pct"] == 78.7
    # Untracked benchmarks must not leak into metrics.
    assert set(entry["metrics"]) == {"gpqa_diamond_pct", "swe_bench_verified_pct"}


def test_epoch_parse_keeps_models_separate():
    out = epoch.parse(EPOCH_CSV)
    entry = next(e for e in out["entries"] if e["raw_name"] == "glm-5.2_max")
    assert entry["metrics"] == {"otis_mock_aime_pct": 86.4}


def test_epoch_data_date_is_max_started_at():
    out = epoch.parse(EPOCH_CSV)
    # Max across ALL rows, including untracked-benchmark ones.
    assert out["data_date"] == "2026-06-30"


def test_epoch_parse_skips_malformed_scores():
    csv_text = HEADER + (
        "r1,GPQA diamond,model-a,2026-06-01T00:00:00Z,not-a-number,\n"
        "r2,GPQA diamond,model-a,2026-06-02T00:00:00Z,,\n"
        "r3,GPQA diamond,model-a,2026-06-03T00:00:00Z,0.5,0.5\n"
    )
    out = epoch.parse(csv_text)
    assert out["entries"] == [
        {"raw_name": "model-a", "metrics": {"gpqa_diamond_pct": 50.0}}
    ]


def test_epoch_parse_empty_csv():
    out = epoch.parse(HEADER)
    assert out == {"entries": [], "data_date": None}
    out = epoch.parse("")
    assert out == {"entries": [], "data_date": None}
