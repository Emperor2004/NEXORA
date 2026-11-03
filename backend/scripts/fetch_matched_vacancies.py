import json
import argparse
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT.parent / "data" / "discovery_runs"

from app.services.document_extraction_service import extract_document
from app.services.linkedin_link_service import normalize_job_url


DEFAULT_BATCH_SIZE = 10


def latest_file(pattern):
    files = sorted(
        DATA_DIR.glob(pattern),
        key=lambda p: p.stat().st_mtime
    )

    if not files:
        raise FileNotFoundError(f"No file found: {pattern}")

    return files[-1]


def completed_vacancy_key(record):
    """Return the candidate/URL key only for a readable successful fetch."""
    if (
        record.get("fetch_status") != "fetched"
        or record.get("extraction_status") != "extracted"
        or not record.get("extracted_text", "").strip()
    ):
        return None
    candidate_id = record.get("candidate_id")
    job_url = normalize_job_url(
        record.get("matched_job_url") or record.get("final_url") or ""
    )
    return (candidate_id, job_url) if candidate_id and job_url else None


def completed_vacancy_keys(paths):
    """Return candidate/URL pairs with a successful text extraction."""
    completed = set()
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        for record in data.get("results", []):
            key = completed_vacancy_key(record)
            if key:
                completed.add(key)
    return completed


def select_batch(candidate_matches, batch_size=DEFAULT_BATCH_SIZE, completed=()):
    if batch_size < 0:
        raise ValueError("batch_size must be zero (all) or a positive integer")

    completed = set(completed)
    pending = []
    seen = set()
    for candidate in candidate_matches:
        urls = candidate.get("matched_job_urls") or []
        if (
            candidate.get("candidate_match_status") != "unique_exact_match"
            or len(urls) != 1
        ):
            continue
        job_url = normalize_job_url(urls[0].get("job_url", ""))
        if not job_url:
            continue
        key = (candidate.get("candidate_id"), job_url)
        if key in completed or key in seen:
            continue
        seen.add(key)
        pending.append(candidate)

    return pending if batch_size == 0 else pending[:batch_size]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Fetch unique exact-match internship vacancy pages."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Number of vacancies to process (0 processes all remaining).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip candidate/URL pairs already fetched with readable text.",
    )
    args = parser.parse_args(argv)
    if args.batch_size < 0:
        parser.error("--batch-size must be zero or a positive integer")

    match_file = latest_file("candidate_url_matches_*.json")
    data = json.loads(match_file.read_text(encoding="utf-8"))

    candidate_matches = data.get("candidate_matches", [])
    eligible_count = sum(
        candidate.get("candidate_match_status") == "unique_exact_match"
        and len(candidate.get("matched_job_urls") or []) == 1
        for candidate in candidate_matches
    )
    existing_outputs = list(DATA_DIR.glob("vacancy_extractions_*.json"))
    completed = (
        completed_vacancy_keys(existing_outputs)
        if args.resume
        else set()
    )
    batch = select_batch(
        candidate_matches,
        batch_size=args.batch_size,
        completed=completed,
    )

    print("Unique exact matches available:", eligible_count)
    if args.resume:
        print("Previously completed candidate/URL pairs:", len(completed))
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
        "resume_enabled": args.resume,
        "eligible_candidates": eligible_count,
        "previously_completed_pairs": len(completed),
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
