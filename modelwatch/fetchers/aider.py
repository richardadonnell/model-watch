import requests
import yaml

SOURCE_ID = "aider"
URL = "https://raw.githubusercontent.com/Aider-AI/aider/main/aider/website/_data/polyglot_leaderboard.yml"


def parse(text: str) -> dict:
    out = []
    dates = []
    for e in yaml.safe_load(text) or []:
        d = e.get("date")
        if d:
            dates.append(str(d))
        out.append(
            {
                "raw_name": str(e["model"]),
                "metrics": {
                    "pass_rate": e.get("pass_rate_2"),
                    "well_formed_pct": e.get("percent_cases_well_formed"),
                    "total_cost": e.get("total_cost"),
                },
            }
        )
    return {"entries": out, "data_date": max(dates) if dates else None}


def fetch() -> dict:
    r = requests.get(URL, timeout=30)
    r.raise_for_status()
    return parse(r.text)
