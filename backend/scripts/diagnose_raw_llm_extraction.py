import json
import logging
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT.parent / "data" / "discovery_runs"

from app.agents.opportunity_extraction_agent import (
    SYSTEM_PROMPT,
    classify_document
)
from app.schemas.opportunity import OpportunityExtraction
from app.services.llm_service import generate_structured_output

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s"
)


def main():
    files = sorted(
        DATA_DIR.glob("vacancy_extractions_*.json"),
        key=lambda path: path.stat().st_mtime
    )

    if not files:
        raise FileNotFoundError("No vacancy extraction input found.")

    input_file = files[-1]
    data = json.loads(input_file.read_text(encoding="utf-8"))

    candidates = [
        item for item in data["results"]
        if item.get("candidate_organization") == "Blue Machines AI"
    ]

    if not candidates:
        raise ValueError("Blue Machines AI record not found.")

    item = candidates[0]
    source_text = item["extracted_text"]
    source_url = item.get("final_url") or item["matched_job_url"]
    source_title = item["candidate_title"]

    document_kind, reason = classify_document(
        source_title,
        source_url,
        source_text
    )

    text_limit = 20_000
    document_text = source_text[:text_limit]

    user_prompt = f"""
SOURCE TITLE:
{source_title}

SOURCE URL:
{source_url}

SOURCE TYPE:
individual_linkedin_job

DOCUMENT TEXT:
{document_text}

DOCUMENT TRUNCATED:
{len(source_text) > text_limit}

Extract information supported by this document.

Do not invent missing values.
Do not combine multiple vacancies.
Provide exact supporting quotations for populated factual fields.
Use the source heading or PDF page reference in source_location.
"""

    schema = OpportunityExtraction.model_json_schema()

    print("\n========== INPUT DIAGNOSTICS ==========")
    print("Candidate:", source_title)
    print("Organization:", item["candidate_organization"])
    print("Source characters:", len(source_text))
    print("Prompt characters:", len(user_prompt))
    print("Classification:", document_kind)
    print("Classification reason:", reason)
    print("Schema fields:", list(OpportunityExtraction.model_fields.keys()))

    print("\nCalling configured LLM provider...")

    raw_result = generate_structured_output(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        output_schema=schema
    )

    print("\n========== RAW MODEL OUTPUT ==========")
    print("Returned keys:", list(raw_result.keys()))

    print("\n========== EXTRACTED VALUES ==========")
    for field in OpportunityExtraction.model_fields:
        if field == "evidence":
            continue
        print(f"{field}: {raw_result.get(field)}")

    print("\n========== RAW EVIDENCE LABELS ==========")
    for index, evidence in enumerate(raw_result.get("evidence", []), 1):
        print(f"\n[{index}]")
        print("Field:", evidence.get("field_name"))
        print("Location:", evidence.get("source_location"))
        print("Quote:", evidence.get("quote"))

    output = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "input_file": input_file.name,
        "candidate_id": item["candidate_id"],
        "candidate_title": source_title,
        "candidate_organization": item["candidate_organization"],
        "source_characters": len(source_text),
        "prompt_characters": len(user_prompt),
        "classification": document_kind,
        "raw_model_output": raw_result
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = DATA_DIR / f"raw_llm_diagnostic_{timestamp}.json"

    output_file.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\nDiagnostic saved:", output_file)


if __name__ == "__main__":
    main()
