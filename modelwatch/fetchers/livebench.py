import csv
import io
import requests

SOURCE_ID = "livebench"
LISTING_URL = (
    "https://api.github.com/repos/livebench/livebench.github.io/contents/public"
)
RAW_BASE = (
    "https://raw.githubusercontent.com/livebench/livebench.github.io/main/public/"
)


def pick_latest_table(files: list[dict]) -> str:
    tables = sorted(
        f["name"]
        for f in files
        if f["name"].startswith("table_") and f["name"].endswith(".csv")
    )
    if not tables:
        raise ValueError("no livebench table found")
    return tables[-1]  # YYYY_MM_DD sorts lexicographically


def parse(csv_text: str) -> list[dict]:
    out = []
    for row in csv.DictReader(io.StringIO(csv_text)):
        name = row.pop("model")
        scores = []
        for v in row.values():
            if v not in ("", None):
                try:
                    scores.append(float(v))
                except ValueError:
                    # Skip non-numeric cells (e.g., "N/A")
                    pass
        avg = round(sum(scores) / len(scores), 2) if scores else None
        out.append({"raw_name": name, "metrics": {"average": avg}})
    return out


def fetch() -> list[dict]:
    listing = requests.get(LISTING_URL, timeout=30)
    listing.raise_for_status()
    table = pick_latest_table(listing.json())
    r = requests.get(RAW_BASE + table, timeout=30)
    r.raise_for_status()
    return parse(r.text)
