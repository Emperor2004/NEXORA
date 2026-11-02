import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT.parent / "data" / "discovery_runs"

from app.services.document_extraction_service import extract_document


BATCH_SIZE = 10


def latest_file(pattern):
    files = sorted(
        DATA_DIR.glob(pattern),
        key=lambda p: p.stat().st_mtime
    )

    if not files:
        raise FileNotFoundError(f"No file found: {pattern}")

    return files[-1]


def main():
    match_file = latest_file("candidate_url_matches_*.json")
    data = json.loads(match_file.read_text(encoding="utf-8"))

    eligible_candidates = [
        candidate
        for candidate in data["candidate_matches"]
        if candidate["candidate_match_status"] == "unique_exact_match"
        and len(candidate["matched_job_urls"]) == 1
    ]

    batch = eligible_candidates[:BATCH_SIZE]

    print("Unique exact matches available:", len(eligible_candidates))
    print("Candidates in this batch:", len(batch))

    results = []

    for index, candidate in enumerate(batch, start=1):
        matched_url = candidate["matched_job_urls"][0]["job_url"]

        print("\n" + "=" * 60)
        print(f"[{index}/{len(batch)}] {candidate['opportunity_title']}")
        print("Organization:", candidate["organization"])
        print("Location:", candidate["location"])
        print("URL:", matched_url)

        extraction = extract_document(matched_url)

        record = {
            "candidate_id": candidate["candidate_id"],
            "candidate_title": candidate["opportunity_title"],
            "candidate_organization": candidate["organization"],
            "candidate_location": candidate["location"],
            "candidate_match_status": candidate["candidate_match_status"],
            "matched_job_url": matched_url,
            "fetch_status": extraction["fetch_status"],
            "final_url": extraction.get("final_url"),
            "http_status": extraction.get("http_status"),
            "document_type": extraction.get("document_type"),
            "extraction_status": extraction["extraction_status"],
            "extracted_text": extraction["extracted_text"],
            "evidence": extraction["evidence"],
            "error": extraction.get("error"),
            "verification_status": "not_verified"
        }

        results.append(record)

        print("Fetch:", record["fetch_status"])
        print("Extraction:", record["extraction_status"])
        print("HTTP status:", record["http_status"])
        print("Extracted characters:", len(record["extracted_text"]))

        if record["error"]:
            print("Error:", record["error"])

    output = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "source_match_file": str(match_file),
        "batch_size": len(batch),
        "successful_fetches": sum(
            item["fetch_status"] == "fetched"
            for item in results
        ),
        "successful_extractions": sum(
            item["extraction_status"] == "extracted"
            for item in results
        ),
        "results": results
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = DATA_DIR / f"vacancy_extractions_{timestamp}.json"

    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\n" + "=" * 60)
    print("VACANCY EXTRACTION SUMMARY")
    print("=" * 60)
    print("Pages attempted:", output["batch_size"])
    print("Successful fetches:", output["successful_fetches"])
    print("Successful extractions:", output["successful_extractions"])
    print("Output:", output_path)


if __name__ == "__main__":
    main()
