import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_DIR = PROJECT_ROOT / "data" / "discovery_runs"

files = sorted(
    DISCOVERY_DIR.glob("extracted_*.json"),
    key=lambda path: path.stat().st_mtime,
    reverse=True,
)

if not files:
    raise FileNotFoundError("No extracted JSON files found.")

with files[0].open("r", encoding="utf-8") as file:
    data = json.load(file)

print(f"Inspecting: {files[0].name}")
print("=" * 75)

for index, record in enumerate(data.get("records", []), start=1):
    search = record.get("search_result", {})
    document = record.get("document", {})

    print(f"\n[{index}] {search.get('title', 'Untitled')}")
    print(f"URL: {search.get('url', '')}")
    print(f"Fetch: {document.get('fetch_status')}")
    print(f"Extraction: {document.get('extraction_status')}")

    extracted_text = document.get("extracted_text", "")
    print(f"Characters: {len(extracted_text)}")

    if extracted_text:
        print("\nEXTRACTED CONTENT PREVIEW:")
        print(extracted_text[:1800])
    else:
        print("No extracted text.")

    evidence = document.get("evidence", [])
    print(f"\nEvidence sections: {len(evidence)}")

    for item in evidence[:3]:
        print(
            f"- {item.get('source_location', 'Unknown location')}: "
            f"{item.get('text', '')[:250]}"
        )

    print("-" * 75)
