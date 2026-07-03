from modelwatch.registry import load_registry


def test_alias_match(tmp_path):
    p = tmp_path / "models.yaml"
    p.write_text("""
models:
  - id: claude-sonnet-5
    name: Claude Sonnet 5
    vendor: Anthropic
    aliases:
      openrouter: ["anthropic/claude-sonnet-5"]
""")
    reg = load_registry(str(p))
    assert (
        reg.canonical_id("openrouter", "anthropic/claude-sonnet-5") == "claude-sonnet-5"
    )


def test_fallback_matches_id_and_name_case_insensitive(tmp_path):
    p = tmp_path / "models.yaml"
    p.write_text("""
models:
  - id: gpt-5
    name: GPT-5
    vendor: OpenAI
    aliases: {}
""")
    reg = load_registry(str(p))
    assert reg.canonical_id("livebench", "GPT-5") == "gpt-5"
    assert reg.canonical_id("aider", "gpt-5") == "gpt-5"


def test_unmatched_returns_none(tmp_path):
    p = tmp_path / "models.yaml"
    p.write_text(
        "models:\n  - id: gpt-5\n    name: GPT-5\n    vendor: OpenAI\n    aliases: {}\n"
    )
    reg = load_registry(str(p))
    assert reg.canonical_id("openrouter", "some/unknown-model") is None
