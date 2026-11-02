import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "discovery_runs"

files = sorted(
    DATA_DIR.glob("extracted_*.json"),
    key=lambda p: p.stat().st_mtime,
    reverse=True
)

with files[0].open("r", encoding="utf-8") as f:
    data = json.load(f)

for record in data["records"]:
    search = record.get("search_result", {})
    document = record.get("document", {})

    url = search.get("url", "")

    if "linkedin.com/jobs/" not in url:
        continue

    text = document.get("extracted_text", "")
    lines = text.splitlines()

    print("\n" + "=" * 80)
    print(search.get("title"))
    print("URL:", url)
    print("Total characters:", len(text))
    print("Total lines:", len(lines))
    print("=" * 80)

    for index, line in enumerate(lines[:100], start=1):
        print(f"{index:03d}: {line[:350]!r}")
