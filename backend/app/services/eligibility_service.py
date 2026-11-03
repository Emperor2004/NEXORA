import re


SUPPORTED_EVIDENCE_STATUSES = {
    "supported_by_source_quote",
    "recovered_from_exact_quote",
}


def _norm(value: str) -> str:
    value = str(value or "").casefold().strip()
    value = re.sub(r"\b(bachelor of technology|bachelor's of technology)\b", "btech", value)
    value = re.sub(r"\b(bachelor of engineering|bachelor's of engineering)\b", "be", value)
    value = re.sub(r"\b(computer science and engineering)\b", "cse", value)
    value = re.sub(r"\b(information technology)\b", "it", value)
    return re.sub(r"[^a-z0-9]+", "", value)


def _matches_any(candidate_values, requirement: str) -> bool:
    alternatives = re.split(r"\s+(?:or|and/or)\s+|[/,;]", requirement, flags=re.I)
    alternatives = [item.strip() for item in alternatives if item.strip()]
    for candidate in candidate_values:
        candidate_norm = _norm(candidate)
        for alternative in alternatives or [requirement]:
            requirement_norm = _norm(alternative)
            if requirement_norm and (
                requirement_norm == candidate_norm
                or requirement_norm in candidate_norm
                or candidate_norm in requirement_norm
            ):
                return True
            if {candidate_norm, requirement_norm} <= {"india", "indian"}:
                return True
    return False


def _supported(record: dict, field_name: str) -> bool:
    field_status = (
        record.get("evidence_validation", {})
        .get("field_validation", {})
        .get(field_name, {})
        .get("status")
    )
    return field_status in SUPPORTED_EVIDENCE_STATUSES


def assess_eligibility(record: dict, candidate_profile: dict | None) -> dict:
    """Conservatively compare explicit, source-supported requirements to a profile."""
    profile = candidate_profile or {}
    extraction = record.get("extraction", record)
    reasons = []
    evaluated_fields = []
    evidence = []
    mismatch = False
    needs_review = False
    unsupported_requirements = set(
        record.get("evidence_validation", {}).get("unsupported_fields", [])
    ).intersection({
        "eligible_degrees",
        "eligible_branches",
        "eligible_years",
        "minimum_cgpa",
        "nationality_requirement",
        "eligibility_summary",
    })
    if unsupported_requirements:
        needs_review = True
        reasons.append(
            "Some extracted eligibility claims were rejected by evidence validation: "
            + ", ".join(sorted(unsupported_requirements))
            + "."
        )

    def note_evidence(field_name):
        evidence.extend(
            item for item in extraction.get("evidence", [])
            if item.get("field_name") == field_name
        )

    list_checks = (
        ("eligible_degrees", "degrees", "degree"),
        ("eligible_branches", "branches", "branch"),
        ("eligible_years", "academic_years", "academic year"),
    )
    for requirement_field, profile_field, label in list_checks:
        requirements = extraction.get(requirement_field) or []
        if not requirements:
            continue
        evaluated_fields.append(requirement_field)
        note_evidence(requirement_field)
        if not _supported(record, requirement_field):
            needs_review = True
            reasons.append(f"The {label} requirement lacks validated evidence.")
            continue
        candidate_values = profile.get(profile_field) or []
        if not candidate_values:
            needs_review = True
            reasons.append(f"Candidate {label} information is missing.")
        elif not any(
            _matches_any(candidate_values, str(requirement))
            for requirement in requirements
        ):
            mismatch = True
            reasons.append(f"Candidate profile does not match the stated {label} requirement.")

    minimum_cgpa = extraction.get("minimum_cgpa")
    if minimum_cgpa not in (None, ""):
        evaluated_fields.append("minimum_cgpa")
        note_evidence("minimum_cgpa")
        match = re.search(r"\d+(?:\.\d+)?", str(minimum_cgpa))
        if not _supported(record, "minimum_cgpa") or not match:
            needs_review = True
            reasons.append("The minimum CGPA requirement is not reliably supported or parseable.")
        elif profile.get("cgpa") is None:
            needs_review = True
            reasons.append("Candidate CGPA is missing.")
        elif float(profile["cgpa"]) < float(match.group(0)):
            mismatch = True
            reasons.append("Candidate CGPA is below the stated minimum.")

    nationality_requirement = extraction.get("nationality_requirement")
    if nationality_requirement:
        evaluated_fields.append("nationality_requirement")
        note_evidence("nationality_requirement")
        if not _supported(record, "nationality_requirement"):
            needs_review = True
            reasons.append("The nationality requirement lacks validated evidence.")
        elif not profile.get("nationality"):
            needs_review = True
            reasons.append("Candidate nationality is missing.")
        elif not _matches_any(
            [profile["nationality"]], str(nationality_requirement)
        ):
            mismatch = True
            reasons.append("Candidate nationality does not match the stated requirement.")

    if extraction.get("eligibility_summary"):
        needs_review = True
        reasons.append("Free-text eligibility requirements need human review.")

    if not evaluated_fields:
        needs_review = True
        reasons.append("No explicit, structured eligibility requirements were extracted.")

    status = "ineligible" if mismatch else "needs_review" if needs_review else "eligible"
    return {
        "status": status,
        "reasons": reasons or ["All extracted structured requirements match the candidate profile."],
        "evaluated_fields": evaluated_fields,
        "evidence": evidence,
    }
