import json
from datetime import datetime, timezone
from unittest.mock import patch
from modelwatch import build


def test_run_writes_outputs(tmp_path):
    (tmp_path / "models.yaml").write_text(
        "models:\n  - id: a-model\n    name: A\n    vendor: V\n"
        "    aliases: {aider: ['a-raw']}\n"
    )
    fake_results = {
        "aider": [{"raw_name": "a-raw", "metrics": {"pass_rate": 50.0}}],
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
