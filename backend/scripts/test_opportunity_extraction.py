import json
import logging
from datetime import datetime
from pathlib import Path

from app.agents.opportunity_extraction_agent import extract_opportunity


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s"
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_DIR = PROJECT_ROOT / "data" / "discovery_runs"


def main():
    files = sorted(
        DISCOVERY_DIR.glob("extracted_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

    if not files:
        raise FileNotFoundError("No extracted document files found.")

    input_file = files[0]

    with input_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    records = data.get("records", [])

    successful_documents = [
        record for record in records
        if (
            record.get("document", {}).get("extraction_status") == "extracted"
            and record.get("document", {}).get("extracted_text", "").strip()
        )
    ]

    print(f"Input: {input_file.name}")
    print(f"Documents with readable text: {len(successful_documents)}")
    print("=" * 65)

    output_records = []

    for index, record in enumerate(successful_documents, start=1):
        search = record.get("search_result", {})
        document = record.get("document", {})

        title = search.get("title", "Untitled")
        url = document.get("final_url") or search.get("url", "")
        text = document.get("extracted_text", "")

        print(f"\n[{index}/{len(successful_documents)}] {title}")

        try:
            result = extract_opportunity(
                source_text=text,
                source_url=url,
                source_title=title,
                source_type=search.get("source_type", "unknown")
            )

            output_records.append(result)

            extraction = result["extraction"]
            validation = result["evidence_validation"]

            print(f"Document kind: {extraction['document_kind']}")
            print(f"Record status: {result['record_status']}")
            print(f"Organization: {extraction['organization']}")
            print(f"Opportunity: {extraction['opportunity_title']}")
            print(f"Paid: {extraction['is_paid']}")
            print(f"Duration: {extraction['duration']}")
            print(f"Deadline: {extraction['application_deadline']}")
            print(
                "Supported fields:",
                sum(
                    item["status"] == "supported_by_source_quote"
                    for item in validation["field_validation"].values()
                )
            )
            print(
                "Unsupported fields:",
                validation["unsupported_fields"]
            )

        except Exception as exc:
            logging.exception("Extraction failed for: %s", title)

            output_records.append({
                "source": {
                    "title": title,
                    "url": url
                },
                "record_status": "extraction_failed",
                "error": f"{type(exc).__name__}: {str(exc)[:500]}",
                "verification_status": "not_independently_verified"
            })

    summary = {
        "created_at": datetime.now().astimezone().isoformat(),
        "input_file": str(input_file),
        "documents_processed": len(successful_documents),
        "individual_announcements": sum(
            item.get("extraction", {}).get("document_kind")
            == "individual_announcement"
            for item in output_records
        ),
        "listing_pages": sum(
            item.get("extraction", {}).get("document_kind")
            == "listing_page"
            for item in output_records
        ),
        "programme_information": sum(
            item.get("extraction", {}).get("document_kind")
            == "programme_information"
            for item in output_records
        ),
        "extraction_failures": sum(
            item.get("record_status") == "extraction_failed"
            for item in output_records
        ),
        "records": output_records
    }

    output_file = DISCOVERY_DIR / (
        f"opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, ensure_ascii=False)

    print("\n" + "=" * 65)
    print("OPPORTUNITY EXTRACTION SUMMARY")
    print("=" * 65)
    print(f"Processed: {summary['documents_processed']}")
    print(f"Individual announcements: {summary['individual_announcements']}")
    print(f"Listing pages: {summary['listing_pages']}")
    print(f"Programme information: {summary['programme_information']}")
    print(f"Extraction failures: {summary['extraction_failures']}")
    print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()
