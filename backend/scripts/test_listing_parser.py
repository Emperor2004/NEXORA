
from app.services.listing_parser import extract_linkedin_listings


combined_layout = """
Data Science Intern Data Science Intern Sony Research India Bengaluru, Karnataka, India 3 weeks ago
Sony Research India

PhD Intern, AI ML in Wireless L1/L2 - Fall 2026 PhD Intern, AI ML in Wireless L1/L2 - Fall 2026 NVIDIA Bengaluru, Karnataka, India 2 weeks ago
NVIDIA

Artificial Intelligence Intern Artificial Intelligence Intern Crossing Infotech India 13 hours ago
Crossing Infotech

AI Agent Engineer Intern AI Agent Engineer Intern Lexsi Labs Mumbai Metropolitan Region 1 day ago
Lexsi Labs
"""

legacy_layout = """
Data Science Intern
Sony Research India
Bengaluru, Karnataka, India
3 weeks ago

PhD Intern, AI ML in Wireless L1/L2 - Fall 2026
NVIDIA
Bengaluru, Karnataka, India
2 weeks ago
"""

print("=" * 65)
print("TEST 1: LINKEDIN COMBINED-ROW FORMAT")
print("=" * 65)

combined_results = extract_linkedin_listings(combined_layout)

for candidate in combined_results:
    print(
        candidate["opportunity_title"],
        "|",
        candidate["organization"],
        "|",
        candidate["location"],
        "|",
        candidate["posting_age"]
    )

assert len(combined_results) == 4, (
    f"Expected 4 combined candidates, got {len(combined_results)}"
)

assert combined_results[0]["opportunity_title"] == "Data Science Intern"
assert combined_results[0]["organization"] == "Sony Research India"
assert combined_results[0]["location"] == "Bengaluru, Karnataka, India"

print("\nCombined-row test passed.")

print("\n" + "=" * 65)
print("TEST 2: LEGACY MULTILINE FORMAT")
print("=" * 65)

legacy_results = extract_linkedin_listings(legacy_layout)

for candidate in legacy_results:
    print(
        candidate["opportunity_title"],
        "|",
        candidate["organization"],
        "|",
        candidate["location"]
    )

assert len(legacy_results) == 2, (
    f"Expected 2 legacy candidates, got {len(legacy_results)}"
)

print("\nLegacy-layout test passed.")

for candidate in combined_results + legacy_results:
    assert candidate["duration"] is None
    assert candidate["eligibility_status"] == "not_assessed"
    assert candidate["verification_status"] == "not_verified"
    assert candidate["discovery_status"] == "unverified_candidate"

print("\nAll parser tests passed.")
