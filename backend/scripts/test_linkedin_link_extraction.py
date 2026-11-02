import json
import sys
from datetime import datetime
from pathlib import Path

# Ensure the backend project root is available for app.* imports.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.linkedin_link_service import extract_links_from_page


DATA_DIR = PROJECT_ROOT.parent / "data" / "discovery_runs"


def latest_file(pattern: str) -> Path:
    files = sorted(
        DATA_DIR.glob(pattern),
        key=lambda path: path.stat().st_mtime
    )

    if not files:
        raise FileNotFoundError(f"No file found for {pattern}")

    return files[-1]


def main():
    candidate_files = [
        latest_file("triage_high_*.json"),
        latest_file("triage_review_*.json")
    ]

    source_pages = {}

    for file_path in candidate_files:
        data = json.loads(file_path.read_text(encoding="utf-8"))

        for candidate in data.get("candidates", []):
            for source in candidate.get("source_pages", []):
                url = source.get("source_page_url")

                if url:
                    source_pages[url] = {
                        "source_page_title": source.get("source_page_title"),
                        "source_page_url": url
                    }

    print("Unique source pages:", len(source_pages))

    page_results = []

    for index, source in enumerate(source_pages.values(), start=1):
        print(f"\n[{index}/{len(source_pages)}] Fetching:")
        print(source["source_page_url"])

        result = extract_links_from_page(source["source_page_url"])
        result["source_page_title"] = source["source_page_title"]

        page_results.append(result)

        print("Fetch status:", result["fetch_status"])
        print("Individual job links:", result["link_count"])

        if result.get("error"):
            print("Error:", result["error"])

    all_links = {}

    for page in page_results:
        for link in page["links"]:
            url = link["job_url"]

            if url not in all_links:
                all_links[url] = link
            else:
                existing = all_links[url]

                if page["source_page_url"] not in existing.get(
                    "also_found_on", []
                ):
                    existing.setdefault("also_found_on", []).append(
                        page["source_page_url"]
                    )

    output = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "source_page_count": len(page_results),
        "successful_pages": sum(
            page["fetch_status"] == "fetched"
            for page in page_results
        ),
        "failed_pages": sum(
            page["fetch_status"] != "fetched"
            for page in page_results
        ),
        "total_link_occurrences": sum(
            page["link_count"] for page in page_results
        ),
        "unique_job_urls": len(all_links),
        "pages": page_results,
        "job_links": list(all_links.values())
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = DATA_DIR / f"linkedin_job_links_{timestamp}.json"

    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\n" + "=" * 55)
    print("LINK EXTRACTION SUMMARY")
    print("=" * 55)
    print("Source pages:", output["source_page_count"])
    print("Successful pages:", output["successful_pages"])
    print("Failed pages:", output["failed_pages"])
    print("Link occurrences:", output["total_link_occurrences"])
    print("Unique individual job URLs:", output["unique_job_urls"])
    print("Output:", output_path)


if __name__ == "__main__":
    main()
