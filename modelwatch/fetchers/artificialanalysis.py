import os
import requests

SOURCE_ID = "artificialanalysis"
URL = "https://artificialanalysis.ai/api/v2/data/llms/models"


def parse(payload: dict) -> list[dict]:
    out = []
    for m in payload["data"]:
        ev = m.get("evaluations") or {}
        pr = m.get("pricing") or {}
        out.append(
            {
                "raw_name": m["slug"],
                "metrics": {
                    "intelligence_index": ev.get(
                        "artificial_analysis_intelligence_index"
                    ),
                    "coding_index": ev.get("artificial_analysis_coding_index"),
                    "price_in_per_1m": pr.get("price_1m_input_tokens"),
                    "price_out_per_1m": pr.get("price_1m_output_tokens"),
                    "price_blended_per_1m": pr.get("price_1m_blended_3_to_1"),
                    "tokens_per_second": m.get("median_output_tokens_per_second"),
                    "ttft_seconds": m.get("median_time_to_first_token_seconds"),
                },
            }
        )
    return out


def fetch() -> dict:
    key = os.environ["ARTIFICIALANALYSIS_API_KEY"]
    r = requests.get(URL, headers={"x-api-key": key}, timeout=30)
    r.raise_for_status()
    return {"entries": parse(r.json()), "data_date": None}
