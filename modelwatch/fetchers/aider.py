import requests
import yaml

SOURCE_ID = "aider"
URL = "https://raw.githubusercontent.com/Aider-AI/aider/main/aider/website/_data/polyglot_leaderboard.yml"


def parse(text: str) -> list[dict]:
    out = []
    for e in yaml.safe_load(text) or []:
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
    return out


def fetch() -> list[dict]:
    r = requests.get(URL, timeout=30)
    r.raise_for_status()
    return parse(r.text)
