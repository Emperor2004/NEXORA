import re


GENERIC_TITLES = {
    "intern",
    "internship",
    "paid internship",
    "research/phd",
    "phd intern",
    "ai internship"
}

GENERIC_ORGANIZATIONS = {
    "company",
    "organization",
    "employer",
    "unknown",
    "not specified",
    "academy"
}

RELEVANCE_PATTERNS = {
    "artificial_intelligence": (
        r"\b(ai|artificial intelligence)\b"
    ),
    "machine_learning": (
        r"\b(machine learning|ml)\b"
    ),
    "deep_learning": (
        r"\bdeep learning\b"
    ),
    "data_science": (
        r"\bdata science\b"
    ),
    "computer_vision": (
        r"\b(computer vision|vision|perception|image processing)\b"
    ),
    "nlp": (
        r"\b(nlp|natural language processing|llm|large language model|speech recognition)\b"
    ),
    "generative_ai": (
        r"\b(generative ai|genai|rag|retrieval augmented generation)\b"
    ),
    "robotics": (
        r"\b(robotics|robotic|autonomous systems|autonomous infrastructure)\b"
    ),
    "research": (
        r"\b(research|scientist)\b"
    ),
    "data_engineering": (
        r"\b(data engineering|data engineer)\b"
    ),
    "ai_agents": (
        r"\b(ai agent|agentic ai|multi.agent)\b"
    ),
    "software_engineering": (
        r"\b(software engineering|software engineer|programming)\b"
    )
}

PHD_PATTERN = re.compile(
    r"\b(phd|ph\.d\.|doctoral|doctorate)\b",
    re.IGNORECASE
)

APPRENTICE_PATTERN = re.compile(
    r"\b(apprentice|apprenticeship)\b",
    re.IGNORECASE
)


def normalize(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def assess_candidate(candidate):
    title = normalize(candidate.get("opportunity_title"))
    organization = normalize(candidate.get("organization"))
    excerpt = normalize(candidate.get("source_excerpt"))

    combined_text = f"{title} {excerpt}"

    relevance_tags = [
        tag
        for tag, pattern in RELEVANCE_PATTERNS.items()
        if re.search(pattern, combined_text, re.IGNORECASE)
    ]

    review_flags = []
    quality_reasons = []

    if not title:
        quality_reasons.append("missing_title")
    elif title.casefold() in GENERIC_TITLES:
        quality_reasons.append("generic_title")

    if not organization:
        quality_reasons.append("missing_organization")
    elif organization.casefold() in GENERIC_ORGANIZATIONS:
        quality_reasons.append("generic_organization")

    if PHD_PATTERN.search(combined_text):
        review_flags.append("explicit_phd_reference")

    if APPRENTICE_PATTERN.search(title):
        review_flags.append("apprenticeship_role")

    if not relevance_tags:
        quality_reasons.append("no_detected_target_domain_relevance")

    if quality_reasons and not relevance_tags:
        triage_tier = "low_relevance"

    elif (
        quality_reasons
        or review_flags
        or not title
        or not organization
    ):
        triage_tier = "needs_eligibility_review"

    else:
        triage_tier = "high_relevance"

    return {
        "triage_tier": triage_tier,
        "relevance_tags": relevance_tags,
        "quality_reasons": quality_reasons,
        "review_flags": review_flags,

        # These fields must be established from individual vacancy evidence.
        "payment_status": candidate.get("payment_status", "unknown"),
        "duration_status": candidate.get("duration_status", "unknown"),
        "eligibility_status": "not_assessed",
        "application_status": candidate.get("application_status", "unknown"),
        "verification_status": candidate.get(
            "verification_status",
            "not_verified"
        )
    }


def triage_candidates(candidates):
    high_relevance = []
    needs_review = []
    low_relevance = []

    for candidate in candidates:
        assessment = assess_candidate(candidate)

        enriched = {
            **candidate,
            **assessment
        }

        if assessment["triage_tier"] == "high_relevance":
            high_relevance.append(enriched)

        elif assessment["triage_tier"] == "needs_eligibility_review":
            needs_review.append(enriched)

        else:
            low_relevance.append(enriched)

    return high_relevance, needs_review, low_relevance
