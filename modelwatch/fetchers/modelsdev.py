import requests

SOURCE_ID = "modelsdev"
# Open-source model catalog (github.com/sst/models.dev, MIT). Costs are USD per 1M tokens.
API_URL = "https://models.dev/api.json"


def parse(payload: dict) -> list[dict]:
    # Payload is {provider_id: {"models": {model_id: {...}}, ...}}. Emit one
    # entry per provider/model; the curated alias list in models.yaml decides
    # which (typically first-party) provider entry is actually tracked.
    out = []
    if not isinstance(payload, dict):
        return out
    for provider_id, provider in payload.items():
        if not isinstance(provider, dict):
            continue
        models = provider.get("models")
        if not isinstance(models, dict):
            continue
        for model_id, m in models.items():
            if not isinstance(m, dict):
                continue
            cost = m.get("cost") if isinstance(m.get("cost"), dict) else {}
            limit = m.get("limit") if isinstance(m.get("limit"), dict) else {}

            def usd_per_1m(key):
                v = cost.get(key)
                # models.dev costs are already USD per 1M tokens — no scaling.
                return round(float(v), 4) if isinstance(v, (int, float)) else None

            out.append(
                {
                    "raw_name": f"{provider_id}/{model_id}",
                    "metrics": {
                        "price_in_per_1m": usd_per_1m("input"),
                        "price_out_per_1m": usd_per_1m("output"),
                        "context_length": limit.get("context"),
                    },
                }
            )
    return out


def fetch() -> dict:
    r = requests.get(API_URL, timeout=60)
    r.raise_for_status()
    return {"entries": parse(r.json()), "data_date": None}
