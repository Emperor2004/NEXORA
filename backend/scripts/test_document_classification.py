import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.opportunity_extraction_agent import classify_document

tests = [
    (
        "AI Growth Engineer",
        "https://www.linkedin.com/jobs/view/ai-growth-engineer-123456",
        "Company Description Role Description Responsibilities"
    ),
    (
        "AI Internship Paid Jobs in India (297 Open Roles)",
        "https://in.linkedin.com/jobs/ai-internship-paid-jobs",
        "Multiple internship roles"
    ),
    (
        "NPTEL Internship Programme",
        "https://example.org/nptel",
        "Eligibility Duration of internship"
    )
]

for title, url, text in tests:
    kind, reason = classify_document(title, url, text)
    print(f"{title}")
    print(f"  Classification: {kind}")
    print(f"  Reason: {reason}\n")

assert classify_document(*tests[0])[0] == "individual_announcement"
assert classify_document(*tests[1])[0] == "listing_page"

print("CLASSIFICATION TESTS PASSED")
