from app.services.candidate_quality_service import assess_candidate
from app.services.eligibility_service import SUPPORTED_EVIDENCE_STATUSES


FIELD_WEIGHTS = {
    "opportunity_title": 1,
    "organization": 1,
    "location": 1,
    "duration": 1,
    "stipend": 1,
    "application_deadline": 1,
    "application_url": 1,
}

DOMAIN_ALIASES = {
    "artificial intelligence": {"artificial_intelligence"},
    "ai": {"artificial_intelligence"},
    "machine learning": {"machine_learning"},
    "ml": {"machine_learning"},
    "computer vision": {"computer_vision"},
    "natural language processing": {"nlp"},
    "nlp": {"nlp"},
    "data science": {"data_science"},
    "robotics": {"robotics"},
    "deep learning": {"deep_learning"},
    "generative ai": {"generative_ai"},
    "research": {"research"},
}


def _target_tags(target_domains):
    tags = set()
    for domain in target_domains or []:
        key = str(domain).strip().casefold()
        tags.update(DOMAIN_ALIASES.get(key, set()))
    return tags


def rank_opportunity(record: dict, candidate_profile: dict | None = None) -> dict:
    extraction = record.get("extraction", {})
    assessment = record.get("eligibility", {})
    profile = candidate_profile or {}

    excerpt = " ".join(
        [
            *(extraction.get("research_areas") or []),
            *(extraction.get("required_skills") or []),
        ]
    )
    quality = assess_candidate({
        "opportunity_title": extraction.get("opportunity_title"),
        "organization": extraction.get("organization"),
        "source_excerpt": excerpt,
    })

    target_tags = _target_tags(profile.get("target_domains"))
    relevance_tags = quality["relevance_tags"]
    matching_tags = target_tags.intersection(relevance_tags)
    if target_tags:
        relevance_score = 20 * len(matching_tags) / len(target_tags)
    else:
        relevance_score = 10 if relevance_tags else 0

    preferred_locations = [
        str(value).strip().casefold()
        for value in profile.get("preferred_locations", [])
        if str(value).strip()
    ]
    opportunity_location = str(extraction.get("location") or "").casefold()
    if not preferred_locations:
        location_score = 2.5
        location_reason = "No location preference supplied; neutral score"
    else:
        location_matches = any(
            preferred in opportunity_location
            or opportunity_location in preferred
            for preferred in preferred_locations
            if opportunity_location
        )
        location_score = 5 if location_matches else 0
        location_reason = (
            "Matches a preferred location"
            if location_matches
            else "No preferred-location match"
        )

    status = assessment.get("status", "needs_review")
    eligibility_score = {
        "eligible": 30,
        "needs_review": 15,
        "ineligible": 0,
    }.get(status, 15)

    field_validation = record.get("evidence_validation", {}).get(
        "field_validation", {}
    )
    supported_count = sum(
        value.get("status") in SUPPORTED_EVIDENCE_STATUSES
        for value in field_validation.values()
    )
    populated_count = sum(
        value not in (None, "", [])
        for key, value in extraction.items()
        if key not in {"document_kind", "evidence", "extraction_notes"}
    )
    evidence_score = (
        25 * supported_count / populated_count if populated_count else 0
    )

    completeness = sum(
        bool(extraction.get(field_name)) * weight
        for field_name, weight in FIELD_WEIGHTS.items()
    )
    completeness_score = 20 * completeness / sum(FIELD_WEIGHTS.values())

    factors = [
        {"name": "eligibility", "score": round(eligibility_score, 2), "max": 30,
         "reason": status},
        {"name": "target_relevance", "score": round(relevance_score, 2), "max": 20,
         "reason": f"Matched tags: {', '.join(sorted(matching_tags)) or 'none'}"},
        {"name": "location_fit", "score": round(location_score, 2), "max": 5,
         "reason": location_reason},
        {"name": "evidence_coverage", "score": round(evidence_score, 2), "max": 25,
         "reason": f"{supported_count}/{populated_count} populated fields supported"},
        {"name": "field_completeness", "score": round(completeness_score, 2), "max": 20,
         "reason": f"{completeness}/{sum(FIELD_WEIGHTS.values())} ranking fields populated"},
    ]
    return {
        "score": round(sum(factor["score"] for factor in factors), 2),
        "factors": factors,
        "relevance_tags": relevance_tags,
    }
