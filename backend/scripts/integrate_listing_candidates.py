import hashlib
import json
from datetime import datetime
from pathlib import Path

from app.services.listing_parser import extract_linkedin_listings


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "discovery_runs"


def latest_file(pattern):
    files = sorted(
        DATA_DIR.glob(pattern),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

    if not files:
        raise FileNotFoundError(
            f"No files matching {pattern} found in {DATA_DIR}"
        )

    return files[0]


def candidate_key(candidate):
    return (
        candidate["opportunity_title"].casefold().strip(),
        candidate["organization"].casefold().strip(),
        candidate["location"].casefold().strip()
    )


def make_candidate_id(candidate):
    raw = "|".join(candidate_key(candidate))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def main():
    source_file = latest_file("extracted_*.json")

    with source_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    unique_candidates = {}
    source_pages_processed = 0
    source_occurrences = 0
    source_errors = []

    for record in data.get("records", []):
        search = record.get("search_result", {})
        document = record.get("document", {})

        source_url = search.get("url", "")
        source_title = (
            search.get("title")
            or document.get("title")
            or "Untitled source"
        )

        if "linkedin.com/jobs/" not in source_url:
            continue

        extracted_text = document.get("extracted_text", "")

        if not extracted_text.strip():
            source_errors.append({
                "source_url": source_url,
                "error": "No extracted text"
            })
            continue

        candidates = extract_linkedin_listings(extracted_text)
        source_pages_processed += 1
        source_occurrences += len(candidates)

        print(f"\nSource: {source_title}")
        print(f"Candidates extracted: {len(candidates)}")

        for candidate in candidates:
            key = candidate_key(candidate)

            if key not in unique_candidates:
                candidate["candidate_id"] = make_candidate_id(candidate)
                candidate["source_pages"] = []
                candidate["source_count"] = 0

                unique_candidates[key] = candidate

            existing = unique_candidates[key]

            source_reference = {
                "source_page_title": source_title,
                "source_page_url": source_url,
                "source_location": candidate["source_location"],
                "source_excerpt": candidate["source_excerpt"]
            }

            if not any(
                item["source_page_url"] == source_url
                for item in existing["source_pages"]
            ):
                existing["source_pages"].append(source_reference)

            existing["source_count"] = len(existing["source_pages"])

    candidates = list(unique_candidates.values())

    candidates.sort(
        key=lambda item: (
            item["organization"].casefold(),
            item["opportunity_title"].casefold()
        )
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = DATA_DIR / f"listing_candidates_{timestamp}.json"

    output = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "input_file": source_file.name,
        "source_pages_processed": source_pages_processed,
        "total_candidate_occurrences": source_occurrences,
        "unique_candidate_count": len(candidates),
        "duplicate_occurrences_removed": (
            source_occurrences - len(candidates)
        ),
        "verification_policy": (
            "Search-result candidates are not verified vacancies. "
            "Individual opportunity pages must be inspected separately."
        ),
        "candidates": candidates,
        "source_errors": source_errors
    }

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(output, file, indent=2, ensure_ascii=False)

    print("\n" + "=" * 65)
    print("NEXORA LISTING INTEGRATION")
    print("=" * 65)
    print(f"Input file: {source_file.name}")
    print(f"Source pages processed: {source_pages_processed}")
    print(f"Candidate occurrences: {source_occurrences}")
    print(f"Unique candidates: {len(candidates)}")
    print(
        "Duplicate occurrences removed:",
        source_occurrences - len(candidates)
    )
    print(f"Output: {output_file}")

    print("\nCandidate preview:")

    for index, candidate in enumerate(candidates[:15], start=1):
        print(f"\n[{index}] {candidate['opportunity_title']}")
        print(f"    Organization: {candidate['organization']}")
        print(f"    Location: {candidate['location']}")
        print(f"    Posting age: {candidate['posting_age']}")
        print(f"    Source pages: {candidate['source_count']}")
        print(f"    Verification: {candidate['verification_status']}")

    print("\nIntegration completed.")


if __name__ == "__main__":
    main()
