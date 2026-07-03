import os
import requests

SOURCE_ID = "llmstats"
URL = "https://api.llm-stats.com/stats/v1/rankings"


def parse(payload: dict) -> list[dict]:
    out = []
    for m in payload.get("data", []):
        out.append(
            {
                "raw_name": m.get("id") or m.get("name"),
                "metrics": {"rating": m.get("rating"), "rank": m.get("rank")},
            }
        )
    return out


def fetch() -> list[dict]:
    key = os.environ["LLMSTATS_API_KEY"]
    r = requests.get(URL, headers={"Authorization": f"Bearer {key}"}, timeout=30)
    r.raise_for_status()
    return parse(r.json())
