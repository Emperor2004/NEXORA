import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT.parent / "data" / "discovery_runs"


def latest_file(pattern):
    files = sorted(
        DATA_DIR.glob(pattern),
        key=lambda p: p.stat().st_mtime
    )
    if not files:
        raise FileNotFoundError(f"No file found: {pattern}")
    return files[-1]


def normalize(value):
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def get_employer_slug(job_url):
    path = unquote(job_url.rstrip("/").split("/")[-1])
    match = re.search(r"-at-(.+)-(\d{6,})$", path)

    if not match:
        return ""

    return normalize(match.group(1))


def main():
    candidate_files = [
        latest_file("triage_high_*.json"),
        latest_file("triage_review_*.json")
    ]

    candidates = []

    for file_path in candidate_files:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        candidates.extend(data.get("candidates", []))

    links_file = latest_file("linkedin_job_links_*.json")
    links_data = json.loads(links_file.read_text(encoding="utf-8"))
    links = links_data.get("job_links", [])

    candidates_by_title = defaultdict(list)

    for candidate in candidates:
        title_key = normalize(candidate.get("opportunity_title"))

        if title_key:
            candidates_by_title[title_key].append(candidate)

    matched_urls = defaultdict(list)
    unmatched_urls = []
    ambiguous_urls = []

    for link in links:
        anchor_title = normalize(link.get("anchor_text"))
        employer_slug = get_employer_slug(link.get("job_url"))

        title_candidates = candidates_by_title.get(anchor_title, [])

        employer_matches = [
            candidate for candidate in title_candidates
            if normalize(candidate.get("organization")) == employer_slug
        ]

        if not employer_matches:
            unmatched_urls.append({
                **link,
                "match_reason": (
                    "No exact title-and-employer match"
                    if title_candidates
                    else "No exact title match"
                )
            })
            continue

        if len(employer_matches) == 1:
            candidate = employer_matches[0]

            matched_urls[candidate["candidate_id"]].append({
                "job_url": link["job_url"],
                "anchor_text": link.get("anchor_text"),
                "employer_slug": employer_slug,
                "match_type": "exact_title_and_employer"
            })
        else:
            ambiguous_urls.append({
                **link,
                "candidate_ids": [
                    candidate["candidate_id"]
                    for candidate in employer_matches
                ],
                "candidate_locations": [
                    candidate.get("location")
                    for candidate in employer_matches
                ],
                "match_reason": (
                    "Multiple candidate records share title and employer"
                )
            })

    candidate_results = []

    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        matches = matched_urls.get(candidate_id, [])

        if len(matches) == 1:
            status = "unique_exact_match"
        elif len(matches) > 1:
            status = "multiple_vacancies_review"
        else:
            status = "no_exact_match"

        candidate_results.append({
            "candidate_id": candidate_id,
            "opportunity_title": candidate.get("opportunity_title"),
            "organization": candidate.get("organization"),
            "location": candidate.get("location"),
            "candidate_match_status": status,
            "matched_job_urls": matches
        })

    output = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "candidate_files": [str(path) for path in candidate_files],
        "links_file": str(links_file),
        "total_candidates": len(candidates),
        "total_job_urls": len(links),
        "unique_exact_candidate_matches": sum(
            item["candidate_match_status"] == "unique_exact_match"
            for item in candidate_results
        ),
        "multiple_vacancies_review": sum(
            item["candidate_match_status"] == "multiple_vacancies_review"
            for item in candidate_results
        ),
        "candidates_without_exact_match": sum(
            item["candidate_match_status"] == "no_exact_match"
            for item in candidate_results
        ),
        "ambiguous_url_count": len(ambiguous_urls),
        "unmatched_url_count": len(unmatched_urls),
        "candidate_matches": candidate_results,
        "ambiguous_urls": ambiguous_urls,
        "unmatched_urls": unmatched_urls
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = DATA_DIR / f"candidate_url_matches_{timestamp}.json"

    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\n" + "=" * 60)
    print("CORRECTED CANDIDATE URL MATCHING")
    print("=" * 60)
    print("Candidates:", output["total_candidates"])
    print("Individual URLs:", output["total_job_urls"])
    print("Unique exact matches:", output["unique_exact_candidate_matches"])
    print("Multiple vacancies requiring review:", output["multiple_vacancies_review"])
    print("Candidates without exact match:", output["candidates_without_exact_match"])
    print("Ambiguous URLs:", output["ambiguous_url_count"])
    print("Unmatched URLs:", output["unmatched_url_count"])
    print("Output:", output_path)

    print("\nREMAINING UNMATCHED URLS:")
    for item in unmatched_urls:
        print(item.get("anchor_text"), "|", item.get("job_url"))


if __name__ == "__main__":
    main()
