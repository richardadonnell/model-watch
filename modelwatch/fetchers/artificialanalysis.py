import os
import requests

SOURCE_ID = "artificialanalysis"
# The legacy /api/v2/data/llms/models route was retired on 2026-11-04 and now
# answers 410 Gone. The documented Free route works for every key tier (Pro and
# Commercial keys get the Free-shape body here), so it is the safe default.
URL = "https://artificialanalysis.ai/api/v2/language/models/free"
MAX_PAGES = 20  # safety cap; the list is ~2 pages of 200 today


def _blended_3_to_1(price_in, price_out):
    # Artificial Analysis's blended price weights input:output tokens 3:1.
    # The Free shape no longer returns it, so derive it from the two prices.
    if price_in is None or price_out is None:
        return None
    return round((3 * price_in + price_out) / 4, 6)


def parse(payload: dict) -> list[dict]:
    out = []
    for m in payload["data"]:
        ev = m.get("evaluations") or {}
        pr = m.get("pricing") or {}
        perf = m.get("performance") or {}
        price_in = pr.get("price_1m_input_tokens")
        price_out = pr.get("price_1m_output_tokens")
        blended = pr.get("price_1m_blended_3_to_1")  # Pro shape only
        if blended is None:
            blended = _blended_3_to_1(price_in, price_out)
        out.append(
            {
                "raw_name": m["slug"],
                "metrics": {
                    "intelligence_index": ev.get(
                        "artificial_analysis_intelligence_index"
                    ),
                    # Artificial Analysis no longer publishes a Coding Index;
                    # the V2 API always returns null for it.
                    "coding_index": ev.get("artificial_analysis_coding_index"),
                    "price_in_per_1m": price_in,
                    "price_out_per_1m": price_out,
                    "price_blended_per_1m": blended,
                    "tokens_per_second": perf.get("median_output_tokens_per_second"),
                    "ttft_seconds": perf.get("median_time_to_first_token_seconds"),
                },
            }
        )
    return out


def fetch() -> dict:
    key = os.environ["ARTIFICIALANALYSIS_API_KEY"]
    entries = []
    page = 1
    while True:
        r = requests.get(
            URL, headers={"x-api-key": key}, params={"page": page}, timeout=30
        )
        r.raise_for_status()
        payload = r.json()
        entries.extend(parse(payload))
        pagination = payload.get("pagination") or {}
        if not pagination.get("has_more") or page >= MAX_PAGES:
            break
        page += 1
    return {"entries": entries, "data_date": None}
