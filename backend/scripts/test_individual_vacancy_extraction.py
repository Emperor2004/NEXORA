import json
import logging
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT.parent / "data" / "discovery_runs"

from app.agents.opportunity_extraction_agent import extract_opportunity


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s"
)


def latest_file(pattern):
    files = sorted(
        DATA_DIR.glob(pattern),
        key=lambda p: p.stat().st_mtime
    )

    if not files:
        raise FileNotFoundError(f"No file found: {pattern}")

    return files[-1]


def main():
    input_file = latest_file("vacancy_extractions_*.json")
    data = json.loads(input_file.read_text(encoding="utf-8"))

    selected_organizations = {
        "Blue Machines AI",
        "Crossing Infotech",
        "Devryxa"
    }

    selected = [
        item for item in data["results"]
        if item["candidate_organization"] in selected_organizations
    ]

    print("Input:", input_file.name)
    print("Selected vacancies:", len(selected))

    results = []

    for index, item in enumerate(selected, start=1):
        print("\n" + "=" * 65)
        print(
            f"[{index}/{len(selected)}] "
            f"{item['candidate_title']} | {item['candidate_organization']}"
        )

        try:
            result = extract_opportunity(
                source_text=item["extracted_text"],
                source_url=item.get("final_url") or item["matched_job_url"],
                source_title=item["candidate_title"],
                source_type="individual_linkedin_job"
            )

            result["candidate_id"] = item["candidate_id"]
            result["candidate_location"] = item["candidate_location"]

            results.append(result)

            extraction = result["extraction"]
            validation = result["evidence_validation"]

            print("Document kind:", extraction["document_kind"])
            print("Record status:", result["record_status"])
            print("Title:", extraction["opportunity_title"])
            print("Organization:", extraction["organization"])
            print("Location:", extraction["location"])
            print("Work mode:", extraction["work_mode"])
            print("Paid:", extraction["is_paid"])
            print("Stipend:", extraction["stipend"])
            print("Duration:", extraction["duration"])
            print("Deadline:", extraction["application_deadline"])
            print("Eligible degrees:", extraction["eligible_degrees"])
            print("Eligible branches:", extraction["eligible_branches"])
            print("Minimum CGPA:", extraction["minimum_cgpa"])
            print("Evidence items:", len(extraction["evidence"]))
            print("Unsupported fields:", validation["unsupported_fields"])

        except Exception as exc:
            logging.exception("Extraction failed")

            results.append({
                "candidate_id": item["candidate_id"],
                "record_status": "extraction_failed",
                "error": f"{type(exc).__name__}: {str(exc)[:500]}"
            })

    output = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "input_file": str(input_file),
        "processed": len(results),
        "successful": sum(
            item.get("record_status") != "extraction_failed"
            for item in results
        ),
        "failed": sum(
            item.get("record_status") == "extraction_failed"
            for item in results
        ),
        "records": results
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = DATA_DIR / f"individual_opportunity_extractions_{timestamp}.json"

    output_file.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\n" + "=" * 65)
    print("LLM EXTRACTION TEST SUMMARY")
    print("=" * 65)
    print("Processed:", output["processed"])
    print("Successful:", output["successful"])
    print("Failed:", output["failed"])
    print("Saved:", output_file)


if __name__ == "__main__":
    main()
