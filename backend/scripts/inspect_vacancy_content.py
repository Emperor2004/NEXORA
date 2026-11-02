import json
from pathlib import Path

DATA_DIR = Path("../data/discovery_runs")

files = sorted(
    DATA_DIR.glob("vacancy_extractions_*.json"),
    key=lambda p: p.stat().st_mtime
)

if not files:
    raise FileNotFoundError("No vacancy extraction file found.")

data = json.loads(files[-1].read_text(encoding="utf-8"))

for index, item in enumerate(data["results"], start=1):
    print("\n" + "=" * 85)
    print(f"{index}. {item['candidate_title']} | {item['candidate_organization']}")
    print("=" * 85)

    text = item.get("extracted_text", "").strip()

    print("Characters:", len(text))
    print("Fetch:", item["fetch_status"])
    print("Extraction:", item["extraction_status"])
    print("Final URL:", item.get("final_url"))
    print("\nCONTENT PREVIEW:\n")
    print(text[:2200] if text else "[NO EXTRACTED TEXT]")
