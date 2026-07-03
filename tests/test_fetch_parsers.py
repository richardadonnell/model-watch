from modelwatch.fetchers import openrouter, artificialanalysis

OR_MODELS = {
    "data": [
        {
            "id": "anthropic/claude-sonnet-5",
            "name": "Anthropic: Claude Sonnet 5",
            "context_length": 1000000,
            "pricing": {"prompt": "0.000002", "completion": "0.00001"},
        }
    ]
}
OR_RANKINGS = {
    "data": [
        {
            "date": "2026-07-02",
            "model_permaslug": "anthropic/claude-sonnet-5",
            "total_completion_tokens": 5,
            "total_prompt_tokens": 95,
            "count": 3,
        },
        {
            "date": "2026-07-02",
            "model_permaslug": "openai/gpt-5",
            "total_completion_tokens": 10,
            "total_prompt_tokens": 40,
            "count": 2,
        },
    ]
}


def test_openrouter_parse_normalizes_price_per_million():
    rows = openrouter.parse(OR_MODELS, OR_RANKINGS)
    row = next(r for r in rows if r["raw_name"] == "anthropic/claude-sonnet-5")
    assert row["metrics"]["price_in_per_1m"] == 2.0
    assert row["metrics"]["price_out_per_1m"] == 10.0
    assert row["metrics"]["tokens_total"] == 100
    assert row["metrics"]["context_length"] == 1000000


AA = {
    "status": 200,
    "data": [
        {
            "id": "uuid-1",
            "name": "Claude Sonnet 5",
            "slug": "claude-sonnet-5",
            "model_creator": {"name": "Anthropic"},
            "evaluations": {
                "artificial_analysis_intelligence_index": 70.1,
                "artificial_analysis_coding_index": 65.2,
            },
            "pricing": {
                "price_1m_input_tokens": 2.0,
                "price_1m_output_tokens": 10.0,
                "price_1m_blended_3_to_1": 4.0,
            },
            "median_output_tokens_per_second": 80.5,
            "median_time_to_first_token_seconds": 0.6,
        }
    ],
}


def test_aa_parse():
    rows = artificialanalysis.parse(AA)
    m = rows[0]["metrics"]
    assert rows[0]["raw_name"] == "claude-sonnet-5"
    assert m["intelligence_index"] == 70.1
    assert m["coding_index"] == 65.2
    assert m["price_blended_per_1m"] == 4.0
    assert m["tokens_per_second"] == 80.5
