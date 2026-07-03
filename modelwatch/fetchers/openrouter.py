import requests

SOURCE_ID = "openrouter"
MODELS_URL = "https://openrouter.ai/api/v1/models"
# Undocumented frontend endpoint (verified 2026-07-03) — may break without notice.
RANKINGS_URL = "https://openrouter.ai/api/frontend/v1/rankings/models"


def parse(models_payload: dict, rankings_payload: dict) -> list[dict]:
    usage: dict[str, int] = {}
    for row in rankings_payload.get("data", []):
        slug = row.get("model_permaslug")
        if slug:
            usage[slug] = (
                usage.get(slug, 0)
                + int(row.get("total_completion_tokens", 0))
                + int(row.get("total_prompt_tokens", 0))
            )
    out = []
    for m in models_payload["data"]:
        p = m.get("pricing") or {}

        def per_1m(key):
            v = p.get(key)
            return round(float(v) * 1_000_000, 4) if v is not None else None

        out.append(
            {
                "raw_name": m["id"],
                "metrics": {
                    "price_in_per_1m": per_1m("prompt"),
                    "price_out_per_1m": per_1m("completion"),
                    "context_length": m.get("context_length"),
                    "tokens_total": usage.get(m["id"]),
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
