import logging
import re

from app.schemas.opportunity import OpportunityExtraction
from app.agents.registry import get_agent_profile
from app.services.llm_service import generate_structured_output
from app.services.linkedin_metadata_parser import parse_linkedin_metadata
from app.services.prompt_registry import load_agent_prompt

logger = logging.getLogger("nexora.opportunity_extraction")


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

    if is_linkedin_login_wall(source_text):
        return "unknown", "linkedin_login_wall_without_vacancy_content"

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


def is_linkedin_login_wall(source_text: str) -> bool:
    text = normalize_text(source_text)
    login_signals = (
        "join or sign in to find your next job",
        "join to apply for the",
        "new to linkedin? join now",
        "by clicking continue to join or sign in",
    )
    return any(signal in text for signal in login_signals) and len(
        strip_linkedin_login_boilerplate(source_text)
    ) < 300


def strip_linkedin_login_boilerplate(source_text: str) -> str:
    text = source_text or ""
    patterns = (
        r"Join or sign in to find your next job",
        r"Join to apply for the .*?\s+role at .*? or New to LinkedIn\? Join now",
        r"By clicking Continue to join or sign in, you agree to LinkedIn[’']s?"
        r" User Agreement\s*,? Privacy Policy\s*,? and Cookie Policy\s*\.?",
        r"New to LinkedIn\? Join now",
    )
    for pattern in patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r"\s+", " ", text).strip()



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


def evidence_supports_value(field_name: str, value, evidence_items: list[dict]) -> bool:
    """Require field evidence to contain the extracted value or its explicit basis."""
    quotes = [normalize_text(item.get("quote", "")) for item in evidence_items]
    quotes = [quote for quote in quotes if quote]
    if not quotes:
        return False

    if isinstance(value, bool):
        joined_quotes = " ".join(quotes)
        if field_name == "is_paid":
            if value:
                return bool(re.search(
                    r"\b(paid|stipend|salary|compensation|remunerat\w*)\b|"
                    r"(?:INR|Rs\.?|₹)\s*\d",
                    joined_quotes,
                    re.IGNORECASE,
                ))
            return bool(re.search(
                r"\b(unpaid|not paid|no stipend|without compensation|volunteer)\b",
                joined_quotes,
                re.IGNORECASE,
            ))
        return False

    if field_name == "stipend_type" and isinstance(value, str):
        joined_quotes = " ".join(quotes)
        condition_patterns = {
            "conditional_performance_based": r"performance[- ]based",
            "conditional_pay_range": r"actual pay (?:will be|is) based on",
            "conditional_completion": (
                r"payable on successful completion|subject to successful completion"
            ),
            "stated_monetary_stipend": (
                r"\b(?:INR|Rs\.?|₹)\s*\d|\bstipend\b"
            ),
        }
        pattern = condition_patterns.get(value)
        return bool(pattern and re.search(pattern, joined_quotes, re.IGNORECASE))

    if field_name == "work_mode" and isinstance(value, str):
        joined_quotes = " ".join(quotes)
        mode_patterns = (
            (r"on[ -]?site|\bWFO\b|in[ -]?office", r"on.site|wfo"),
            (r"\bremote\b|work from home", r"remote|work from home"),
            (r"\bhybrid\b", r"hybrid"),
        )
        # The output value can expand common abbreviations such as WFO.
        for value_pattern, quote_pattern in mode_patterns:
            if re.search(value_pattern, value, re.IGNORECASE):
                return bool(re.search(quote_pattern, joined_quotes, re.IGNORECASE))

    def comparable(value_text: str) -> str:
        return re.sub(r"[^\w]+", " ", normalize_text(value_text)).strip()

    if isinstance(value, list):
        return all(
            any(comparable(str(item)) in comparable(quote) for quote in quotes)
            for item in value
        )

    return any(comparable(str(value)) in comparable(quote) for quote in quotes)


def validate_and_sanitize_evidence(
    extraction: OpportunityExtraction,
    source_text: str,
    metadata_evidence: list[dict] | None = None,
) -> tuple[OpportunityExtraction, dict]:
    """
    Validate evidence quotations against source text, canonicalize aliases,
    and recover only narrowly defined exact scalar values.
    """
    normalized_source = normalize_text(source_text)
    metadata_values = {
        item["field_name"]: normalize_text(item["quote"])
        for item in metadata_evidence or []
    }

    evidence_by_field = {}
    canonical_evidence = []

    for item in extraction.evidence:
        canonical_field = canonicalize_evidence_field(item.field_name)

        if canonical_field is None:
            continue

        normalized_quote = normalize_text(item.quote)

        is_metadata_quote = (
            item.source_location == "Matched vacancy candidate metadata"
            and metadata_values.get(canonical_field) == normalized_quote
        )
        normalized_location = normalize_text(item.source_location)
        generic_page_locations = {
            "linkedin vacancy page",
            "page content",
            "source document",
        }
        is_page_quote = bool(
            normalized_quote
            and normalized_quote in normalized_source
            and normalized_location
            and (
                normalized_location in generic_page_locations
                or normalized_location in normalized_source
            )
        )
        if not normalized_quote or not (is_page_quote or is_metadata_quote):
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

        if matching_evidence and evidence_supports_value(
            field_name, value, matching_evidence
        ):
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

            reason = (
                "Evidence does not support the extracted value."
                if matching_evidence
                else "No matching field-specific source quotation."
            )
            rejected_claims.append({
                "field": field_name,
                "rejected_value": value,
                "reason": reason
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
    source_type: str = "unknown",
    candidate_metadata: dict | None = None,
    timeout_seconds: int = 120,
    max_output_tokens: int = 4096,
    allowed_providers: tuple[str, ...] | list[str] | None = None,
) -> dict:

    if not source_text or not source_text.strip():
        raise ValueError("Source text is empty.")

    document_kind, classification_reason = classify_document(
        source_title=source_title,
        source_url=source_url,
        source_text=source_text
    )

    if classification_reason == "linkedin_login_wall_without_vacancy_content":
        empty_extraction = OpportunityExtraction(document_kind="unknown")
        return {
            "source": {
                "title": source_title,
                "url": source_url,
                "source_type": source_type,
                "document_truncated": False,
                "characters_analyzed": len(source_text),
            },
            "classification": {
                "document_kind": "unknown",
                "method": "deterministic_rules",
                "reason": classification_reason,
            },
            "record_status": "source_login_wall",
            "extraction": empty_extraction.model_dump(),
            "evidence_validation": {
                "field_validation": {},
                "rejected_claims": [],
                "unsupported_fields": [],
                "recovered_fields": [],
                "all_populated_fields_supported": True,
            },
            "verification_status": "not_independently_verified",
        }

    # Keep the initial context bounded for the local 3B model.
    text_limit = 20_000
    truncated = len(source_text) > text_limit
    original_document_text = source_text[:text_limit]
    document_text = strip_linkedin_login_boilerplate(original_document_text)

    user_prompt = f"""
SOURCE TITLE:
{source_title}

SOURCE URL:
{source_url}

SOURCE TYPE:
{source_type}

MATCHED CANDIDATE METADATA (identity/location context only):
{candidate_metadata or {}}

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

    profile = get_agent_profile("opportunity_extractor")
    prompt = load_agent_prompt("opportunity_extractor")
    raw_result = generate_structured_output(
        system_prompt=f"{profile.system_instructions}\n\n{prompt['content']}",
        user_prompt=user_prompt,
        output_schema=OpportunityExtraction.model_json_schema(),
        timeout_seconds=timeout_seconds or profile.timeout_seconds,
        max_output_tokens=max_output_tokens or profile.max_output_tokens,
        allowed_providers=allowed_providers or profile.allowed_providers,
    )

    metadata_evidence = []
    if "linkedin.com/jobs/view/" in source_url.casefold():
        candidate_metadata = candidate_metadata or {}
        parsed_metadata = parse_linkedin_metadata(
            source_text=document_text,
            candidate_title=candidate_metadata.get("candidate_title"),
            candidate_organization=candidate_metadata.get("candidate_organization"),
            candidate_location=candidate_metadata.get("candidate_location"),
        )
        metadata_evidence.extend(parsed_metadata["evidence"])
        for field_name in ("opportunity_title", "organization", "location"):
            value = parsed_metadata.get(field_name)
            if (
                value
                and parsed_metadata.get("field_sources", {}).get(field_name)
                == "matched_candidate_metadata"
            ):
                metadata_evidence.append({
                    "field_name": field_name,
                    "source_location": "Matched vacancy candidate metadata",
                    "quote": value,
                })
        deterministic_fields = set()
        for field_name in (
            "opportunity_title", "organization", "location", "work_mode",
            "employment_type", "duration", "stipend", "stipend_type", "is_paid"
        ):
            value = parsed_metadata.get(field_name)
            if (
                field_name == "is_paid"
                and parsed_metadata.get("stipend_type")
                and parsed_metadata.get("stipend_type").startswith("conditional_")
            ):
                raw_result[field_name] = None
                deterministic_fields.add(field_name)
                continue
            if value is not None:
                raw_result[field_name] = value
                deterministic_fields.add(field_name)

        # Evidence emitted for a value that was replaced by deterministic
        # metadata can be misleading even when its quote appears on the page.
        existing_evidence = raw_result.get("evidence")
        if not isinstance(existing_evidence, list):
            existing_evidence = []
        raw_result["evidence"] = [
            item for item in existing_evidence
            if not isinstance(item, dict)
            or canonicalize_evidence_field(item.get("field_name", ""))
            not in deterministic_fields
        ]
        raw_result["evidence"].extend(metadata_evidence)

    # Deterministic classification takes precedence over the LLM prediction.
    raw_result["document_kind"] = document_kind

    extraction = OpportunityExtraction.model_validate(raw_result)

    sanitized_extraction, evidence_result = validate_and_sanitize_evidence(
        extraction=extraction,
        source_text=original_document_text,
        metadata_evidence=metadata_evidence,
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
