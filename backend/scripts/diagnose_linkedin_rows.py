import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "discovery_runs"

files = sorted(
    DATA_DIR.glob("extracted_*.json"),
    key=lambda p: p.stat().st_mtime,
    reverse=True
)

if not files:
    raise FileNotFoundError("No extracted_*.json files found.")

with files[0].open("r", encoding="utf-8") as f:
    data = json.load(f)

POSTING_AGE_PATTERN = re.compile(
    r"(?i)(?:\d+\s+(?:minutes?|hours?|days?|weeks?|months?|years?)\s+ago|"
    r"just now|today|yesterday)\s*$"
)

print(f"Inspecting: {files[0].name}")

for record in data.get("records", []):
    search = record.get("search_result", {})
    document = record.get("document", {})

    url = search.get("url", "")

    if "linkedin.com/jobs/" not in url:
        continue

    text = document.get("extracted_text", "")
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    print("\n" + "=" * 75)
    print("SOURCE:", url)
    print("TOTAL NON-EMPTY LINES:", len(lines))

    matches = 0

    for index, line in enumerate(lines):
        if POSTING_AGE_PATTERN.search(line):
            matches += 1

            print(f"\nMATCH {matches}")
            print("ROW:", repr(line))
            print(
                "NEXT LINE:",
                repr(lines[index + 1]) if index + 1 < len(lines) else "<NONE>"
            )

            if matches >= 12:
                break

    if matches == 0:
        print("\nNO POSTING-AGE MATCHES FOUND.")
        print("First 20 non-empty lines:")

        for line in lines[:20]:
            print(repr(line))