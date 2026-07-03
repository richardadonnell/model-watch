from modelwatch.fetchers import openrouter, artificialanalysis

OR_MODELS = {
    "data": [
        {
            "id": "anthropic/claude-sonnet-5",
            "name": "Anthropic: Claude Sonnet 5",
            "context_length": 1000000,
            "pricing": {"prompt": "0.000002", "completion": "0.00001"},
        },
        {
            "id": "cohere/command-a",
            "name": "Cohere: Command A",
            "canonical_slug": "cohere/command-a",
            "context_length": 256000,
            "pricing": {"prompt": "0.0000025", "completion": "0.00001"},
        },
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
        {
            # Versioned permaslug — differs from the models-endpoint id
            # "cohere/command-a" by a version suffix.
            "date": "2026-07-02",
            "model_permaslug": "cohere/command-a-03-2025",
            "total_completion_tokens": 200,
            "total_prompt_tokens": 800,
            "count": 7,
        },
        {
            # Present-but-null token field must be treated as 0, not crash.
            "date": "2026-07-02",
            "model_permaslug": "openai/gpt-5",
            "total_completion_tokens": None,
            "total_prompt_tokens": 10,
            "count": 1,
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


def test_openrouter_parse_joins_versioned_permaslug():
    # rankings permaslug "cohere/command-a-03-2025" must map onto the
    # models-endpoint id "cohere/command-a" via version-suffix match.
    rows = openrouter.parse(OR_MODELS, OR_RANKINGS)
    row = next(r for r in rows if r["raw_name"] == "cohere/command-a")
    assert row["metrics"]["tokens_total"] == 1000


def test_openrouter_parse_handles_null_token_counts():
    # A present-but-null token field must not raise (fail-soft the source).
    rows = openrouter.parse(OR_MODELS, OR_RANKINGS)
    assert rows  # did not raise


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


from modelwatch.fetchers import aider, livebench

AIDER_YAML = """
- dirname: 2026-06-01-x
  model: claude-sonnet-5
  edit_format: diff
  pass_rate_2: 82.2
  percent_cases_well_formed: 99.1
  total_cost: 12.34
  date: 2026-06-01
"""


def test_aider_parse():
    res = aider.parse(AIDER_YAML)
    rows = res["entries"]
    assert res["data_date"] == "2026-06-01"
    assert rows[0]["raw_name"] == "claude-sonnet-5"
    assert rows[0]["metrics"]["pass_rate"] == 82.2
    assert rows[0]["metrics"]["total_cost"] == 12.34


LB_CSV = (
    "model,code_completion,code_generation,python\nclaude-sonnet-5,80.0,90.0,85.0\n"
)


def test_livebench_parse_averages_all_tasks():
    rows = livebench.parse(LB_CSV)
    assert rows[0]["raw_name"] == "claude-sonnet-5"
    assert rows[0]["metrics"]["average"] == 85.0


def test_livebench_parse_skips_non_numeric_cells():
    csv = (
        "model,code_completion,code_generation,python\nclaude-sonnet-5,80.0,N/A,85.0\n"
    )
    rows = livebench.parse(csv)
    assert rows[0]["raw_name"] == "claude-sonnet-5"
    # Average only over numeric cells: (80.0 + 85.0) / 2 = 82.5
    assert rows[0]["metrics"]["average"] == 82.5


def test_livebench_parse_all_empty_cells():
    csv = "model,code_completion,code_generation,python\nclaude-sonnet-5,,,\n"
    rows = livebench.parse(csv)
    assert rows[0]["raw_name"] == "claude-sonnet-5"
    assert rows[0]["metrics"]["average"] is None


def test_livebench_pick_latest_release():
    files = [
        {"name": "table_2024_06_24.csv"},
        {"name": "table_2026_01_08.csv"},
        {"name": "categories_2026_01_08.json"},
    ]
    assert livebench.pick_latest_table(files) == "table_2026_01_08.csv"


def test_livebench_release_date_from_filename():
    assert livebench.release_date_from_filename("table_2026_01_08.csv") == "2026-01-08"
