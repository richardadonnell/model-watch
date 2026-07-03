from scripts.format_suggestions import format_body


def test_non_empty_groups_by_source_and_includes_raw_name():
    suggestions = [
        {
            "source": "artificialanalysis",
            "raw_name": "Shiny New Model",
            "metric": "intelligence_index",
            "value": 85.0,
        },
        {
            "source": "aider",
            "raw_name": "Coder X",
            "metric": "pass_rate",
            "value": 72.0,
        },
    ]
    body = format_body(suggestions)
    assert "Shiny New Model" in body
    assert "Coder X" in body
    assert "artificialanalysis" in body
    assert "aider" in body
    assert "models.yaml" in body


def test_empty_returns_no_suggestions_message():
    body = format_body([])
    assert "no new" in body.lower()
