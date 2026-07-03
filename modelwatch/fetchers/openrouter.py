import requests

SOURCE_ID = "openrouter"
MODELS_URL = "https://openrouter.ai/api/v1/models"
# Undocumented frontend endpoint (verified 2026-07-03) — may break without notice.
RANKINGS_URL = "https://openrouter.ai/api/frontend/v1/rankings/models"


def parse(models_payload: dict, rankings_payload: dict) -> list[dict]:
    # Usage is keyed by the rankings payload's model_permaslug, which is NOT
    # 1:1 with the models-endpoint id: versioned models have a dated permaslug
    # (e.g. "cohere/command-a-03-2025") whose base id is "cohere/command-a".
    # `or 0` guards against present-but-null (JSON null -> None) token fields.
    usage: dict[str, int] = {}
    for row in rankings_payload.get("data", []):
        slug = row.get("model_permaslug")
        if slug:
            usage[slug] = (
                usage.get(slug, 0)
                + int(row.get("total_completion_tokens") or 0)
                + int(row.get("total_prompt_tokens") or 0)
            )
    out = []
    for m in models_payload["data"]:
        p = m.get("pricing") or {}

        def per_1m(key):
            v = p.get(key)
            return round(float(v) * 1_000_000, 4) if v is not None else None

        # Sum usage across every permaslug that maps to this model: exact id
        # match, canonical_slug match, or a version-suffix ("<id>-...") match.
        mid = m["id"]
        canonical = m.get("canonical_slug")
        matched = [
            v
            for slug, v in usage.items()
            if slug == mid or slug == canonical or slug.startswith(mid + "-")
        ]
        tokens_total = sum(matched) if matched else None

        out.append(
            {
                "raw_name": mid,
                "metrics": {
                    "price_in_per_1m": per_1m("prompt"),
                    "price_out_per_1m": per_1m("completion"),
                    "context_length": m.get("context_length"),
                    "tokens_total": tokens_total,
                },
            }
        )
    return out


def fetch() -> list[dict]:
    models = requests.get(MODELS_URL, timeout=30)
    models.raise_for_status()
    rankings = requests.get(RANKINGS_URL, timeout=30)
    rankings.raise_for_status()
    return parse(models.json(), rankings.json())
