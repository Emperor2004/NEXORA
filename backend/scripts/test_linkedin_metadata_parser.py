import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "tests" / "fixtures" / "discovery_runs"

from app.services.linkedin_metadata_parser import parse_linkedin_metadata


def latest_file(pattern):
    files = sorted(
        DATA_DIR.glob(pattern),
        key=lambda p: p.stat().st_mtime
    )
    if not files:
        raise FileNotFoundError(pattern)
    return files[-1]


def main():
    input_file = latest_file("vacancy_extractions_*.json")
    data = json.loads(input_file.read_text(encoding="utf-8"))

    records = [
        item for item in data["results"]
        if item.get("extraction_status") == "extracted"
        and item.get("extracted_text", "").strip()
    ]

    assert len(records) == 10, (
        f"Expected 10 readable vacancy records, found {len(records)}"
    )

    print("Input:", input_file.name)

    results = []

    for index, item in enumerate(records, 1):
        parsed = parse_linkedin_metadata(
            source_text=item.get("extracted_text", ""),
            candidate_title=item.get("candidate_title"),
            candidate_organization=item.get("candidate_organization"),
            candidate_location=item.get("candidate_location")
        )

        results.append(parsed)

        print("\n" + "=" * 60)
        print(f"[{index}] {item['candidate_title']}")
        for key in (
            "opportunity_title",
            "organization",
            "location",
            "work_mode",
            "employment_type",
            "duration",
            "stipend",
            "stipend_type",
            "is_paid",
        ):
            print(f"{key}: {parsed[key]}")

    # Regression assertions for known source content.
    blue = results[4]
    assert blue["duration"] == "3-6 Months"
    assert blue["location"] == "Bengaluru"
    assert blue["work_mode"] == "On-site (WFO)"
    assert blue["employment_type"] == "Internship"
    assert blue["is_paid"] is None

    crossing_ai = results[6]
    assert crossing_ai["duration"] == "1 to 3 months"
    assert crossing_ai["work_mode"] == "Remote"
    assert crossing_ai["stipend"] == (
        "INR 15,500 to INR 16,500 per month"
    )

    crossing_ml = results[7]
    assert crossing_ml["duration"] == "1 to 3 months"
    assert crossing_ml["work_mode"] == "Remote"
    assert crossing_ml["stipend"] == (
        "INR 15,500 to INR 16,500 per month"
    )

    devryxa = results[9]
    assert devryxa["duration"] == "3 Months"
    assert devryxa["work_mode"] == "Remote"
    assert devryxa["stipend_type"] == "conditional_performance_based"

    print("\nALL REGRESSION ASSERTIONS PASSED")


if __name__ == "__main__":
    main()
