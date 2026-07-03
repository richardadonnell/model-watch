import yaml


def test_sources_yaml_valid():
    with open("sources.yaml", encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    sources = doc["sources"]
    assert len(sources) >= 21
    fetched = {s["id"] for s in sources if s.get("fetched")}
    assert fetched == {
        "openrouter",
        "artificialanalysis",
        "aider",
        "livebench",
        "llmstats",
    }
    for s in sources:
        assert s["url"].startswith("https://")
        assert s["tier"] in range(1, 7)
