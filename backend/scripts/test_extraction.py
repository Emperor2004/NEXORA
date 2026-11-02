import json
import time
from datetime import datetime
from pathlib import Path

from app.services.document_extraction_service import extract_document


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_DIR = PROJECT_ROOT / "data" / "discovery_runs"


def main():
    search_files = sorted(
        DISCOVERY_DIR.glob("search_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not search_files:
        raise FileNotFoundError(
            f"No search result JSON files found in {DISCOVERY_DIR}"
        )

    source_file = search_files[0]

    with source_file.open("r", encoding="utf-8") as file:
        search_data = json.load(file)

    results = search_data.get("results", [])

    if not results:
        print("The latest search file contains no results.")
        return

    print(f"Input file: {source_file.name}")
    print(f"Documents to process: {len(results)}")
    print("-" * 55)

    extracted_documents = []

    for index, item in enumerate(results, start=1):
        url = item.get("url")

        print(f"\n[{index}/{len(results)}] {item.get('title', 'Untitled')}")
        print(f"URL: {url}")

        if not url:
            print("Skipped: result has no URL.")
            continue

        document = extract_document(url)

        record = {
            "search_result": item,
            "document": document,
        }

        extracted_documents.append(record)

        print(f"Fetch status: {document['fetch_status']}")
        print(f"Document type: {document['document_type']}")
        print(f"Extraction status: {document['extraction_status']}")
        print(f"Extracted characters: {len(document['extracted_text'])}")

        if document.get("error"):
            print(f"Note: {document['error']}")

        # Avoid sending requests too rapidly to the same search-result sources.
        time.sleep(1)

    output = {
        "created_at": datetime.now().astimezone().isoformat(),
        "input_file": str(source_file),
        "documents_processed": len(extracted_documents),
        "documents_fetched": sum(
            item["document"]["fetch_status"] == "fetched"
            for item in extracted_documents
        ),
        "documents_with_text": sum(
            item["document"]["extraction_status"] == "extracted"
            for item in extracted_documents
        ),
        "records": extracted_documents,
    }

    output_file = DISCOVERY_DIR / (
        f"extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(output, file, indent=2, ensure_ascii=False)

    print("\n" + "=" * 55)
    print("EXTRACTION SUMMARY")
    print("=" * 55)
    print(f"Processed: {output['documents_processed']}")
    print(f"Fetched: {output['documents_fetched']}")
    print(f"Text extracted: {output['documents_with_text']}")
    print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()
