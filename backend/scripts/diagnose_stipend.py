import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "discovery_runs"

files = sorted(
    DATA_DIR.glob("vacancy_extractions_*.json"),
    key=lambda p: p.stat().st_mtime
)

if not files:
    raise FileNotFoundError(
        f"No vacancy_extractions_*.json files found in: {DATA_DIR}"
    )

input_file = files[-1]
data = json.loads(input_file.read_text(encoding="utf-8"))

print("Input:", input_file.name)
print("Data directory:", DATA_DIR)

for item in data["results"]:
    if item.get("candidate_organization") != "Crossing Infotech":
        continue

    print("\n" + "=" * 70)
    print(item.get("candidate_title"))

    text = re.sub(r"\s+", " ", item.get("extracted_text", ""))

    matches = list(re.finditer(
        r"INR\s*15,500.{0,100}",
        text,
        re.IGNORECASE
    ))

    if not matches:
        print("No matching stipend phrase found.")
        continue

    for match in matches:
        start = max(0, match.start() - 100)
        end = min(len(text), match.end() + 100)

        print("\nMATCH:")
        print(text[start:end])
