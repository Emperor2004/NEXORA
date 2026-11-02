import logging
import re

from app.schemas.opportunity import OpportunityExtraction
from app.services.llm_service import generate_structured_output

logger = logging.getLogger("nexora.opportunity_extraction")


SYSTEM_PROMPT = """
You are NEXORA's evidence-grounded internship information extraction agent.

Extract only information explicitly stated in the supplied document.

STRICT RULES:
1. Never invent information.
2. Use null for missing scalar values and [] for missing lists.
3. Preserve dates, stipend, duration and eligibility wording as written.
4. Do not assume an internship is currently open.
5. Do not assume an internship is paid without explicit evidence.
6. Do not assume external students are eligible.
7. Do not treat a search-results page as one individual vacancy.
8. Every populated factual field must have at least one evidence item.
9. Evidence quotations must be copied verbatim from the supplied text.
10. Use the supplied heading or PDF page reference as source_location.
11. Do not combine multiple organizations into one organization field.
12. If a page contains multiple vacancies, do not invent one combined vacancy.
13. Posting age (e.g. "3 weeks ago") must only be extracted into posting_age.
14. Never use posting age as internship duration.
15. Duration must describe the internship engagement period, not the age of a job listing.

DOCUMENT CLASSIFICATION:
- individual_announcement: one specific internship vacancy.
- listing_page: multiple separate vacancies or search results.
- programme_information: general details about one internship programme.
- institutional_portal: a general portal where opportunities may be posted.
- unknown: insufficient information to classify.

Return only data matching the supplied JSON schema.
"""


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def classify_document(
    source_title: str,
    source_url: str,
    source_text: str
) -> tuple[str, str]:
    """
    Deterministic classification using identifiable page characteristics.
    This classification overrides the LLM's document_kind prediction.
    """
    title = source_title.casefold()
    url = source_url.casefold()
    text = source_text.casefold()

    # An individual LinkedIn vacancy detail page is not a search-results page.
    if "linkedin.com/jobs/view/" in url:
        return "individual_announcement", "individual_linkedin_job_detail_page"

    # Job-board search pages and pages listing multiple vacancies.
    if (
        ("linkedin.com/jobs/" in url and "/jobs/view/" not in url)
        or "glassdoor." in url
        or re.search(r"\d+\s+(open\s+)?(roles|jobs)\b", title)
    ):
        return "listing_page", "job_board_or_multiple_job_results"

    if (
        "title institution(s) eligibility area duration" in text
        or (
            "internships view" in text
            and "institution(s)" in text
            and "eligibility" in text
        )
    ):
        return "listing_page", "institutional_internship_listing_table"

    # General institutional portal.
    if (
        "internship & placement portal" in text
        or (
            "for companies" in text
            and "for academia" in text
            and "for students" in text
            and "portal" in title
        )
    ):
        return "institutional_portal", "general_institutional_portal"

    # General programme information, rather than an individual vacancy.
    if (
        "nptel" in title
        and "eligibility" in text
        and "duration of internship" in text
    ):
        return "programme_information", "nptel_programme_information"

    # Explicit announcement language.
    announcement_patterns = [
        r"applications are invited",
        r"invites applications",
        r"advertisement for .*internship",
        r"apply on or before",
        r"last date for submission",
    ]

    if any(re.search(pattern, text) for pattern in announcement_patterns):
        return "individual_announcement", "explicit_vacancy_announcement_language"

    return "unknown", "insufficient_deterministic_classification_signals"



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


def extract_opportunity(
    source_text: str,
    source_url: str,
    source_title: str = "",
    source_type: str = "unknown"
) -> dict:

    if not source_text or not source_text.strip():
        raise ValueError("Source text is empty.")

    document_kind, classification_reason = classify_document(
        source_title=source_title,
        source_url=source_url,
        source_text=source_text
    )

    # Keep the initial context bounded for the local 3B model.
    text_limit = 20_000
    truncated = len(source_text) > text_limit
    document_text = source_text[:text_limit]

    user_prompt = f"""
SOURCE TITLE:
{source_title}

SOURCE URL:
{source_url}

SOURCE TYPE:
{source_type}

DOCUMENT TEXT:
{document_text}

DOCUMENT TRUNCATED:
{truncated}

Extract information supported by this document.

Do not invent missing values.
Do not combine multiple vacancies.
Provide exact supporting quotations for populated factual fields.
Use the source heading or PDF page reference in source_location.
"""

    raw_result = generate_structured_output(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        output_schema=OpportunityExtraction.model_json_schema()
    )

    # Deterministic classification takes precedence over the LLM prediction.
    raw_result["document_kind"] = document_kind

    extraction = OpportunityExtraction.model_validate(raw_result)

    sanitized_extraction, evidence_result = validate_and_sanitize_evidence(
        extraction=extraction,
        source_text=document_text
    )

    if document_kind == "individual_announcement":
        if evidence_result["unsupported_fields"]:
            record_status = "needs_human_review"
        else:
            record_status = "candidate_for_human_review"
    else:
        record_status = "not_an_individual_opportunity"

    return {
        "source": {
            "title": source_title,
            "url": source_url,
            "source_type": source_type,
            "document_truncated": truncated,
            "characters_analyzed": len(document_text)
        },
        "classification": {
            "document_kind": document_kind,
            "method": "deterministic_rules",
            "reason": classification_reason
        },
        "record_status": record_status,
        "extraction": sanitized_extraction.model_dump(),
        "evidence_validation": evidence_result,
        "verification_status": "not_independently_verified"
    }
