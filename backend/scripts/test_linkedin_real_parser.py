import json
from pathlib import Path

from app.services.listing_parser import extract_linkedin_listings


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "discovery_runs"

files = sorted(
    DATA_DIR.glob("extracted_*.json"),
    key=lambda p: p.stat().st_mtime,
    reverse=True
)

if not files:
    raise FileNotFoundError("No extraction files found.")

with files[0].open("r", encoding="utf-8") as file:
    data = json.load(file)

total = 0

for record in data.get("records", []):

    search = record.get("search_result", {})
    document = record.get("document", {})

    url = search.get("url", "")

    if "linkedin.com/jobs/" not in url:
        continue

    source_text = document.get("extracted_text", "")
    candidates = extract_linkedin_listings(source_text)

    print("\n" + "=" * 70)
    print(search.get("title"))
    print(f"Candidates: {len(candidates)}")

    for candidate in candidates[:10]:
        print(
            f"\nTitle: {candidate['opportunity_title']}"
            f"\nCompany: {candidate['organization']}"
            f"\nLocation: {candidate['location']}"
            f"\nPosting age: {candidate['posting_age']}"
        )

        assert candidate["duration"] is None
        assert candidate["discovery_status"] == "unverified_candidate"

    total += len(candidates)

print("\n" + "=" * 70)
print(f"TOTAL CANDIDATES: {total}")
print("Real-data parser test completed.")
