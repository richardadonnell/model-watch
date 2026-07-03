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


def release_date_from_filename(name: str) -> str:
    # "table_2026_01_08.csv" -> "2026-01-08"
    stem = name[len("table_") :].rsplit(".", 1)[0]
    return stem.replace("_", "-")


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


def fetch() -> dict:
    listing = requests.get(LISTING_URL, timeout=30)
    listing.raise_for_status()
    table = pick_latest_table(listing.json())
    r = requests.get(RAW_BASE + table, timeout=30)
    r.raise_for_status()
    return {
        "entries": parse(r.text),
        "data_date": release_date_from_filename(table),
    }
