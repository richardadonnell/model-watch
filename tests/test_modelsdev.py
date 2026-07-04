from modelwatch.fetchers import modelsdev

MD = {
    "anthropic": {
        "id": "anthropic",
        "name": "Anthropic",
        "models": {
            "claude-sonnet-5": {
                "id": "claude-sonnet-5",
                "name": "Claude Sonnet 5",
                "limit": {"context": 1000000, "output": 64000},
                "cost": {
                    "input": 2,
                    "output": 10,
                    "cache_read": 0.2,
                    "cache_write": 2.5,
                },
            },
            # Free/unpriced entry: no cost block at all.
            "claude-lab-free": {
                "id": "claude-lab-free",
                "name": "Claude Lab Free",
                "limit": {"context": 200000},
            },
        },
    },
    "openai": {
        "id": "openai",
        "name": "OpenAI",
        "models": {
            "gpt-5.5": {
                "id": "gpt-5.5",
                "name": "GPT-5.5",
                "limit": {"context": 400000},
                "cost": {"input": 1.25, "output": 10},
            }
        },
    },
    # Provider with malformed models value must be skipped, not crash.
    "broken-provider": {"id": "broken-provider", "models": None},
}


def test_modelsdev_parse_prices_already_per_million():
    rows = modelsdev.parse(MD)
    row = next(r for r in rows if r["raw_name"] == "anthropic/claude-sonnet-5")
    # models.dev costs are USD per 1M tokens already — passed through unscaled.
    assert row["metrics"]["price_in_per_1m"] == 2.0
    assert row["metrics"]["price_out_per_1m"] == 10.0
    assert row["metrics"]["context_length"] == 1000000


def test_modelsdev_parse_emits_provider_slash_model_per_provider():
    rows = modelsdev.parse(MD)
    names = {r["raw_name"] for r in rows}
    assert "anthropic/claude-sonnet-5" in names
    assert "openai/gpt-5.5" in names


def test_modelsdev_parse_missing_cost_yields_none_metrics():
    rows = modelsdev.parse(MD)
    row = next(r for r in rows if r["raw_name"] == "anthropic/claude-lab-free")
    assert row["metrics"]["price_in_per_1m"] is None
    assert row["metrics"]["price_out_per_1m"] is None
    assert row["metrics"]["context_length"] == 200000


def test_modelsdev_parse_handles_empty_and_malformed():
    assert modelsdev.parse({}) == []
    assert modelsdev.parse(None) == []
    assert modelsdev.parse({"x": "not-a-dict"}) == []
    # broken-provider (models: None) is skipped without raising
    assert all("broken-provider" not in r["raw_name"] for r in modelsdev.parse(MD))
