import pytest

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
    assert reg.canonical_id("openrouter", "gpt-5") == "gpt-5"


def test_colliding_alias_raises_value_error(tmp_path):
    p = tmp_path / "models.yaml"
    p.write_text("""
models:
  - id: model-a
    name: Model A
    vendor: VendorA
    aliases:
      openrouter: ["shared-alias"]
  - id: model-b
    name: Model B
    vendor: VendorB
    aliases:
      openrouter: ["shared-alias"]
""")
    with pytest.raises(ValueError):
        load_registry(str(p))


def test_same_canonical_id_reregistration_does_not_raise(tmp_path):
    p = tmp_path / "models.yaml"
    p.write_text("""
models:
  - id: model-a
    name: Model A
    vendor: VendorA
    aliases:
      openrouter: ["model-a", "same-alias"]
      other: ["same-alias"]
""")
    # Should not raise: "model-a" as id creates a wildcard entry that
    # matches the openrouter alias "model-a" for the SAME canonical id.
    reg = load_registry(str(p))
    assert reg.canonical_id("openrouter", "model-a") == "model-a"
    assert reg.canonical_id("openrouter", "same-alias") == "model-a"
    assert reg.canonical_id("other", "same-alias") == "model-a"


def test_source_alias_takes_precedence_over_wildcard(tmp_path):
    p = tmp_path / "models.yaml"
    p.write_text("""
models:
  - id: model-a
    name: Model A
    vendor: VendorA
    aliases:
      x: ["model-b"]
  - id: model-b
    name: Model B
    vendor: VendorB
    aliases: {}
""")
    reg = load_registry(str(p))
    # "model-b" is model A's source-specific alias for source "x",
    # and is also model B's canonical id (wildcard entry).
    assert reg.canonical_id("x", "model-b") == "model-a"
    assert reg.canonical_id("other-source", "model-b") == "model-b"


def test_unmatched_returns_none(tmp_path):
    p = tmp_path / "models.yaml"
    p.write_text(
        "models:\n  - id: gpt-5\n    name: GPT-5\n    vendor: OpenAI\n    aliases: {}\n"
    )
    reg = load_registry(str(p))
    assert reg.canonical_id("openrouter", "some/unknown-model") is None
