import json
from datetime import datetime, timezone
from unittest.mock import patch
from modelwatch import build


def test_run_writes_outputs(tmp_path):
    (tmp_path / "models.yaml").write_text(
        "models:\n  - id: a-model\n    name: A\n    vendor: V\n"
        "    aliases: {aider: ['a-raw']}\n"
    )
    (tmp_path / "sources.yaml").write_text("sources: []\n")
    fake_results = {
        "aider": {
            "entries": [{"raw_name": "a-raw", "metrics": {"pass_rate": 50.0}}],
            "data_date": "2026-06-01",
        },
        "openrouter": None,
        "artificialanalysis": None,
        "livebench": None,
        "llmstats": None,
    }
    with patch.object(build, "run_fetchers", return_value=fake_results):
        build.run(str(tmp_path), datetime(2026, 7, 3, tzinfo=timezone.utc))
    latest = json.loads((tmp_path / "data" / "latest.json").read_text())
    assert latest["models"]["a-model"]["scores"]["aider"]["pass_rate"] == 50.0
    assert latest["changes"] == []  # first run
    assert (tmp_path / "data" / "history" / "2026-07-03.json").exists()
    trends = json.loads((tmp_path / "data" / "trends.json").read_text())
    assert trends["a-model"]["aider"]["pass_rate"] == [["2026-07-03", 50.0]]
    sources = json.loads((tmp_path / "data" / "sources.json").read_text())
    assert sources == {"sources": []}


def test_run_survives_corrupt_latest_json(tmp_path):
    (tmp_path / "models.yaml").write_text(
        "models:\n  - id: a-model\n    name: A\n    vendor: V\n"
        "    aliases: {aider: ['a-raw']}\n"
    )
    (tmp_path / "sources.yaml").write_text("sources: []\n")
    fake_results = {
        "aider": {
            "entries": [{"raw_name": "a-raw", "metrics": {"pass_rate": 50.0}}],
            "data_date": "2026-06-01",
        },
        "openrouter": None,
        "artificialanalysis": None,
        "livebench": None,
        "llmstats": None,
    }
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "latest.json").write_text("not valid json {{{", encoding="utf-8")
    with patch.object(build, "run_fetchers", return_value=fake_results):
        snap = build.run(str(tmp_path), datetime(2026, 7, 3, tzinfo=timezone.utc))
    assert snap["changes"] == []  # treated as first run


def test_build_trends_skips_malformed_history_file(tmp_path):
    (tmp_path / "models.yaml").write_text(
        "models:\n  - id: a-model\n    name: A\n    vendor: V\n"
        "    aliases: {aider: ['a-raw']}\n"
    )
    (tmp_path / "sources.yaml").write_text("sources: []\n")
    fake_results = {
        "aider": {
            "entries": [{"raw_name": "a-raw", "metrics": {"pass_rate": 50.0}}],
            "data_date": "2026-06-01",
        },
        "openrouter": None,
        "artificialanalysis": None,
        "livebench": None,
        "llmstats": None,
    }
    with patch.object(build, "run_fetchers", return_value=fake_results):
        build.run(str(tmp_path), datetime(2026, 7, 3, tzinfo=timezone.utc))
    history_dir = tmp_path / "data" / "history"
    (history_dir / "garbage.json").write_text("not json", encoding="utf-8")
    trends = build._build_trends(history_dir)
    assert trends["a-model"]["aider"]["pass_rate"] == [["2026-07-03", 50.0]]
