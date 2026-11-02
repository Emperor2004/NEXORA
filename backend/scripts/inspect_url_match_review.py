import json
from pathlib import Path

data_dir = Path("../data/discovery_runs")

files = sorted(
    data_dir.glob("candidate_url_matches_*.json"),
    key=lambda p: p.stat().st_mtime
)

if not files:
    raise FileNotFoundError("Candidate matching output not found.")

data = json.loads(files[-1].read_text(encoding="utf-8"))

print("\nMULTIPLE VACANCIES REQUIRING REVIEW")
print("=" * 65)

for candidate in data["candidate_matches"]:
    if candidate["candidate_match_status"] == "multiple_vacancies_review":
        print("\nCandidate:", candidate["opportunity_title"])
        print("Organization:", candidate["organization"])
        print("Location:", candidate["location"])
        print("Candidate ID:", candidate["candidate_id"])

        for match in candidate["matched_job_urls"]:
            print("  URL:", match["job_url"])
            print("  Anchor:", match["anchor_text"])

print("\nAMBIGUOUS IBM URLS")
print("=" * 65)

for item in data["ambiguous_urls"]:
    print("\nAnchor:", item["anchor_text"])
    print("Locations:", item["candidate_locations"])
    print("Candidate IDs:", item["candidate_ids"])
    print("URL:", item["job_url"])

print("\nCANDIDATES WITHOUT EXACT MATCH")
print("=" * 65)

for candidate in data["candidate_matches"]:
    if candidate["candidate_match_status"] == "no_exact_match":
        print(
            candidate["opportunity_title"],
            "|",
            candidate["organization"],
            "|",
            candidate["location"]
        )
