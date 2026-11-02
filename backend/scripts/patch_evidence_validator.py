from pathlib import Path

schema_path = Path("app/schemas/opportunity.py")
agent_path = Path("app/agents/opportunity_extraction_agent.py")

schema = schema_path.read_text(encoding="utf-8")

schema_anchor = "    work_mode: str | None = None\n"

if "    employment_type: str | None = None\n" not in schema:
    if schema.count(schema_anchor) != 1:
        raise RuntimeError("Could not safely locate work_mode in schema.")

    schema = schema.replace(
        schema_anchor,
        schema_anchor + "    employment_type: str | None = None\n",
        1
    )
    schema_path.write_text(schema, encoding="utf-8")
    print("Added employment_type to OpportunityExtraction.")
else:
    print("employment_type already exists.")

agent = agent_path.read_text(encoding="utf-8")

start_marker = "def validate_and_sanitize_evidence("
end_marker = "\ndef extract_opportunity("

if agent.count(start_marker) != 1 or agent.count(end_marker) != 1:
    raise RuntimeError("Could not safely locate evidence validator boundaries.")

start = agent.index(start_marker)
end = agent.index(end_marker)

new_function = r'''
def canonicalize_evidence_field(field_name: str) -> str | None:
    """
    Map common LLM evidence labels to canonical schema field names.
    Unknown labels are ignored rather than treated as valid evidence.
    """
    aliases = {
        "title": "opportunity_title",
        "job_title": "opportunity_title",
        "position_title": "opportunity_title",
        "job_duration": "duration",
        "internship_duration": "duration",
        "job_location": "location",
        "work_location": "location",
        "company": "organization",
        "company_name": "organization",
        "employer": "organization",
        "employment_type": "employment_type",
        "work_arrangement": "work_mode",
        "eligibility": "eligibility_summary",
        "deadline": "application_deadline",
        "stipend_amount": "stipend",
    }

    normalized = re.sub(
        r"[\s\-]+",
        "_",
        str(field_name).strip().casefold()
    )

    canonical = aliases.get(normalized, normalized)

    if canonical not in OpportunityExtraction.model_fields:
        return None

    if canonical in {
        "document_kind",
        "evidence",
        "extraction_notes"
    }:
        return None

    return canonical


def recover_exact_scalar_value(field_name: str, quote: str):
    """
    Recover only values whose quotation is itself a recognizable scalar.
    Never infer payment, eligibility, or other facts from broad text.
    """
    value = quote.strip()

    if not value:
        return None

    if field_name == "opportunity_title":
        return value

    if field_name == "duration":
        pattern = (
            r"\d+\s*(?:-|–|to)\s*\d+\s*"
            r"(?:days?|weeks?|months?|years?)"
            r"|\d+\s*(?:days?|weeks?|months?|years?)"
        )
        if re.fullmatch(pattern, value, flags=re.IGNORECASE):
            return value

    if field_name == "employment_type":
        allowed = {
            "internship",
            "full-time internship",
            "part-time internship",
            "full time",
            "part time",
            "contract",
            "temporary",
        }
        if value.casefold() in allowed:
            return value

    return None


def validate_and_sanitize_evidence(
    extraction: OpportunityExtraction,
    source_text: str
) -> tuple[OpportunityExtraction, dict]:
    """
    Validate evidence quotations against source text, canonicalize aliases,
    and recover only narrowly defined exact scalar values.
    """
    normalized_source = normalize_text(source_text)

    evidence_by_field = {}
    canonical_evidence = []

    for item in extraction.evidence:
        canonical_field = canonicalize_evidence_field(item.field_name)

        if canonical_field is None:
            continue

        normalized_quote = normalize_text(item.quote)

        if not normalized_quote or normalized_quote not in normalized_source:
            continue

        evidence_record = {
            "field_name": canonical_field,
            "source_location": item.source_location,
            "quote": item.quote
        }

        canonical_evidence.append(evidence_record)

        evidence_by_field.setdefault(canonical_field, []).append({
            "source_location": item.source_location,
            "quote": item.quote
        })

    data = extraction.model_dump()
    data["evidence"] = canonical_evidence

    field_validation = {}
    rejected_claims = []
    recovered_fields = []

    for field_name, value in data.items():

        if field_name in {
            "document_kind",
            "evidence",
            "extraction_notes"
        }:
            continue

        matching_evidence = evidence_by_field.get(field_name, [])

        is_populated = (
            value is not None
            and value != ""
            and value != []
        )

        if not is_populated and matching_evidence:
            # Recovery is deliberately limited to exact scalar quotations.
            for evidence_item in matching_evidence:
                recovered = recover_exact_scalar_value(
                    field_name,
                    evidence_item["quote"]
                )

                if recovered is not None:
                    data[field_name] = recovered
                    value = recovered
                    is_populated = True
                    recovered_fields.append(field_name)
                    break

        if not is_populated:
            field_validation[field_name] = {
                "status": "not_found",
                "evidence": matching_evidence
            }
            continue

        if matching_evidence:
            field_validation[field_name] = {
                "status": (
                    "recovered_from_exact_quote"
                    if field_name in recovered_fields
                    else "supported_by_source_quote"
                ),
                "evidence": matching_evidence
            }
        else:
            field_validation[field_name] = {
                "status": "unsupported_removed",
                "evidence": []
            }

            rejected_claims.append({
                "field": field_name,
                "rejected_value": value,
                "reason": "No matching field-specific source quotation."
            })

            if isinstance(value, list):
                data[field_name] = []
            else:
                data[field_name] = None

    sanitized_extraction = OpportunityExtraction.model_validate(data)

    return sanitized_extraction, {
        "field_validation": field_validation,
        "rejected_claims": rejected_claims,
        "unsupported_fields": [
            claim["field"] for claim in rejected_claims
        ],
        "recovered_fields": sorted(set(recovered_fields)),
        "all_populated_fields_supported": len(rejected_claims) == 0
    }

'''

agent = agent[:start] + new_function + agent[end:]
agent_path.write_text(agent, encoding="utf-8")

print("Updated evidence validator with canonical field aliases.")
print("Added exact-quote recovery for title, duration and employment type.")
