import json
from pathlib import Path

data_dir = Path("../data/discovery_runs")

for pattern in ["triage_high_*.json", "triage_review_*.json"]:
    files = sorted(data_dir.glob(pattern), key=lambda p: p.stat().st_mtime)

    if not files:
        print(f"\nNo file found: {pattern}")
        continue

    path = files[-1]
    data = json.loads(path.read_text(encoding="utf-8"))

    print(f"\n{'=' * 70}")
    print("FILE:", path.name)
    print("ROOT TYPE:", type(data).__name__)

    if isinstance(data, dict):
        print("ROOT KEYS:", list(data.keys()))

        for key, value in data.items():
            if isinstance(value, list) and value:
                print("CANDIDATE COLLECTION:", key)
                print("COUNT:", len(value))
                print("FIRST CANDIDATE:")
                print(json.dumps(value[0], indent=2, ensure_ascii=False))
                break

    elif isinstance(data, list) and data:
        print("COUNT:", len(data))
        print("FIRST CANDIDATE:")
        print(json.dumps(data[0], indent=2, ensure_ascii=False))
