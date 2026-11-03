"""Check source/evidence fixture integrity; this script does not run a model."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "models" / "evaluations" / "cases" / "opportunity-evidence.jsonl"


def main():
    case_count = 0
    field_count = 0
    failures = []
    for line_number, line in enumerate(FIXTURE.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        case = json.loads(line)
        case_count += 1
        source = case.get("source_text", "")
        if not source:
            failures.append(f"line {line_number}: source_text is empty")
        for field, item in case.get("fields", {}).items():
            value, quote = item.get("value"), item.get("quote")
            if value is None:
                if quote is not None:
                    failures.append(f"line {line_number}: unknown {field} has a quote")
                continue
            field_count += 1
            if not quote or quote not in source:
                failures.append(f"line {line_number}: {field} quote is not an exact source substring")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        raise SystemExit(1)
    print(
        f"PASS: {case_count} synthetic cases and {field_count} populated-field quotes are internally consistent. "
        "No model was called; these counts are not accuracy metrics."
    )


if __name__ == "__main__":
    main()
