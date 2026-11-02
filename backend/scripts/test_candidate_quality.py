import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from app.services.candidate_quality_service import triage_candidates


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "discovery_runs"


def latest_file(pattern):
    files = sorted(
        DATA_DIR.glob(pattern),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

    if not files:
        raise FileNotFoundError(f"No {pattern} file found.")

    return files[0]


def save_json(path, payload):
    with path.open("w", encoding="utf-8") as file:
        json.dump(
            payload,
            file,
            indent=2,
            ensure_ascii=False
        )


def main():
    source_file = latest_file("listing_candidates_*.json")

    with source_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    candidates = data.get("candidates", [])

    high, review, low = triage_candidates(candidates)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    outputs = {
        "high_relevance": (
            DATA_DIR / f"triage_high_{timestamp}.json",
            high
        ),
        "needs_review": (
            DATA_DIR / f"triage_review_{timestamp}.json",
            review
        ),
        "low_relevance": (
            DATA_DIR / f"triage_low_{timestamp}.json",
            low
        )
    }

    for tier, (path, records) in outputs.items():
        save_json(path, {
            "generated_at": datetime.now().astimezone().isoformat(),
            "input_file": source_file.name,
            "triage_tier": tier,
            "total_candidates": len(records),
            "candidates": records
        })

    print("\nNEXORA CANDIDATE TRIAGE REPORT")
    print("=" * 65)
    print(f"Input file: {source_file.name}")
    print(f"Total candidates: {len(candidates)}")

    print(f"\nHigh relevance: {len(high)}")
    print(f"Needs eligibility review: {len(review)}")
    print(f"Low relevance: {len(low)}")

    print("\nHIGH-RELEVANCE CANDIDATES")
    print("-" * 65)

    for item in high:
        print(
            f"{item['opportunity_title']} | "
            f"{item['organization']} | "
            f"{item['location']} | "
            f"{', '.join(item['relevance_tags'])}"
        )

    print("\nCANDIDATES NEEDING REVIEW")
    print("-" * 65)

    for item in review:
        print(
            f"{item['opportunity_title']} | "
            f"{item['organization']} | "
            f"Flags: {', '.join(item['review_flags'])} | "
            f"Reasons: {', '.join(item['quality_reasons'])}"
        )

    print("\nLOW-RELEVANCE CANDIDATES")
    print("-" * 65)

    for item in low:
        print(
            f"{item['opportunity_title']} | "
            f"{item['organization']} | "
            f"{', '.join(item['quality_reasons'])}"
        )

    print("\nOUTPUT FILES")
    print("-" * 65)

    for tier, (path, records) in outputs.items():
        print(f"{tier}: {path}")
        print(f"Records: {len(records)}")

    print("\nSTATUS COUNTS")
    print("-" * 65)

    print(
        "Verification:",
        dict(Counter(
            item["verification_status"] for item in candidates
        ))
    )

    print(
        "Eligibility:",
        dict(Counter(
            item["eligibility_status"] for item in candidates
        ))
    )

    print("\nTriage completed.")


if __name__ == "__main__":
    main()
