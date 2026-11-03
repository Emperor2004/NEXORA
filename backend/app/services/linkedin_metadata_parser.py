import re


def clean(value):
    if not value:
        return None
    return re.sub(r"\s+", " ", value).strip(" \t\r\n:;,")


NEXT_FIELD = (
    r"Duration|Stipend|Employment Type|Work Mode|Location|"
    r"Experience Level|Responsibilities|Required Skills|"
    r"Eligibility|Benefits|Seniority Level|Job Title|Company|"
    r"About the Company|About the Role"
)

SECTION_BOUNDARY = (
    r"Responsibilities|Required Skills|Eligibility|Benefits|"
    r"About the Company|About the Role|Equal Opportunity|"
    r"Seniority level"
)


def capture_labeled(label, text):
    pattern = (
        rf"\b{re.escape(label)}\s*:\s*(.*?)"
        rf"(?=\s+(?:{NEXT_FIELD})\s*:|"
        rf"\s+(?:{SECTION_BOUNDARY})\b|$)"
    )
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return clean(match.group(1)) if match else None


def source_quote(value, text):
    if not value:
        return None
    match = re.search(re.escape(value), text, re.IGNORECASE)
    return match.group(0) if match else None


def parse_linkedin_metadata(
    source_text,
    candidate_title=None,
    candidate_organization=None,
    candidate_location=None
):
    text = re.sub(r"\s+", " ", source_text or "").strip()

    result = {
        "opportunity_title": None,
        "organization": None,
        "location": None,
        "work_mode": None,
        "employment_type": None,
        "duration": None,
        "stipend": None,
        "stipend_type": None,
        "is_paid": None,
        "evidence": [],
        "field_sources": {},
    }

    def assign(field, value, source="page_text"):
        value = clean(value)
        if not value:
            return

        result[field] = value
        result["field_sources"][field] = source

        quote = source_quote(value, text)
        if quote:
            result["evidence"].append({
                "field_name": field,
                "source_location": "LinkedIn vacancy page",
                "quote": quote,
            })

    # Candidate metadata is the authoritative matched identity.
    if candidate_title:
        title = re.sub(
            r"\s*\|\s*Remote\s*$",
            "",
            candidate_title,
            flags=re.IGNORECASE
        )
        assign(
            "opportunity_title",
            title,
            "matched_candidate_metadata"
        )
    else:
        assign(
            "opportunity_title",
            capture_labeled("Job Title", text)
        )

    company = candidate_organization or capture_labeled("Company", text)
    if company:
        source = (
            "matched_candidate_metadata"
            if candidate_organization
            else "page_text"
        )
        assign("organization", company, source)

    # Duration: accept only a recognizable engagement period.
    duration = capture_labeled("Duration", text)

    if not duration:
        match = re.search(
            r"\b\d+\s*(?:-|–|to)\s*\d+\s*"
            r"(?:days?|weeks?|months?|years?)\b",
            text,
            re.IGNORECASE
        )
        duration = match.group(0) if match else None

    if duration:
        duration_match = re.match(
            r"\d+\s*(?:(?:-|–|to)\s*\d+\s*)?"
            r"(?:days?|weeks?|months?|years?)\b",
            duration,
            re.IGNORECASE
        )
        duration = duration_match.group(0) if duration_match else None
    if duration:
        assign("duration", duration)

    # Stipend: capture only a monetary amount and its relevant qualifier.
    stipend_pattern = (
        r"Performance[- ]based,\s*up to\s*"
        r"(?:INR|Rs\.?|₹)\s*\d[\d,]*(?:/-|/|-)?"
        r"|(?:INR|Rs\.?|₹)\s*\d[\d,]*"
        r"(?:\s*(?:to|-|–)\s*(?:(?:INR|Rs\.?|₹)\s*)?\d[\d,]*)?"
        r"(?:\s*(?:per month|/month))?"
    )

    # Prefer the explicitly labelled stipend field over introductory
    # or benefits text, which may contain abbreviated duplicates.
    stipend_source = capture_labeled("Stipend", text)
    if stipend_source:
        stipend_search_text = stipend_source
    else:
        stipend_mentions = list(re.finditer(r"\bstipend\b", text, re.IGNORECASE))
        stipend_search_text = " ".join(
            text[match.start():match.end() + 140]
            for match in stipend_mentions
        )

    stipend_match = re.search(
        stipend_pattern,
        stipend_search_text,
        re.IGNORECASE
    )

    if stipend_match:
        stipend = clean(stipend_match.group(0))
        assign("stipend", stipend)

        conditional_pay_context = re.search(
            r"(?:actual pay (?:will be|is) based on|performance[- ]based)",
            text,
            re.IGNORECASE,
        )
        conditional_completion_context = re.search(
            r"(?:payable on successful completion|subject to successful completion)",
            text,
            re.IGNORECASE,
        )
        if re.search(r"performance[- ]based", stipend, re.IGNORECASE):
            result["stipend_type"] = "conditional_performance_based"
        elif conditional_pay_context:
            result["stipend_type"] = "conditional_pay_range"
        elif conditional_completion_context:
            result["stipend_type"] = "conditional_completion"
        else:
            result["stipend_type"] = "stated_monetary_stipend"
        result["field_sources"]["stipend_type"] = result["field_sources"].get(
            "stipend", "page_text"
        )
        stipend_quote = source_quote(stipend, text)
        condition_match = (
            conditional_pay_context
            or conditional_completion_context
        )
        condition_quote = (
            condition_match.group(0)
            if condition_match
            else None
        )
        if condition_quote:
            condition_quote = source_quote(condition_quote, text)
        type_quote = condition_quote or stipend_quote
        if type_quote:
            result["evidence"].append({
                "field_name": "stipend_type",
                "source_location": "LinkedIn vacancy page",
                "quote": type_quote,
            })
        if not result["stipend_type"].startswith("conditional_"):
            result["is_paid"] = True
            result["field_sources"]["is_paid"] = "explicit_stipend_evidence"
            if stipend_quote:
                result["evidence"].append({
                    "field_name": "is_paid",
                    "source_location": "LinkedIn vacancy page",
                    "quote": stipend_quote,
                })

    # Employment type: bounded to a known employment value.
    employment = capture_labeled("Employment Type", text)

    if employment:
        employment_match = re.match(
            r"(Internship|Full[- ]?Time\s*\(Internship\)|"
            r"Part[- ]?Time\s*\(Internship\)|"
            r"Full[- ]?Time|Part[- ]?Time)",
            employment,
            re.IGNORECASE
        )
        if employment_match:
            assign("employment_type", employment_match.group(0))
    elif re.search(r"Seniority level\s+Internship", text, re.IGNORECASE):
        assign(
            "employment_type",
            "Internship"
        )

    # Work mode: explicit labels first, then WFO/remote indicators.
    work_mode = capture_labeled("Work Mode", text)

    if work_mode:
        mode_match = re.match(
            r"(Remote|Hybrid|On[- ]site|WFO|Work from home)",
            work_mode,
            re.IGNORECASE
        )
        work_mode = mode_match.group(0) if mode_match else None

    if not work_mode:
        if re.search(r"\bWFO\b", text, re.IGNORECASE):
            work_mode = "On-site (WFO)"
        elif re.search(r"\bRemote\b", text, re.IGNORECASE):
            work_mode = "Remote"
        elif re.search(r"\bHybrid\b", text, re.IGNORECASE):
            work_mode = "Hybrid"

    if work_mode:
        assign("work_mode", work_mode)
        if not any(
            item["field_name"] == "work_mode"
            for item in result["evidence"]
        ):
            mode_evidence_patterns = {
                "On-site (WFO)": r"\bWFO\b|on[ -]?site",
                "Remote": r"\bremote\b|work from home",
                "Hybrid": r"\bhybrid\b",
            }
            mode_match = re.search(
                mode_evidence_patterns.get(work_mode, r"(?!)"),
                text,
                re.IGNORECASE,
            )
            if mode_match:
                result["evidence"].append({
                    "field_name": "work_mode",
                    "source_location": "LinkedIn vacancy page",
                    "quote": mode_match.group(0),
                })

    # Location: prefer a compact explicit location field.
    location = capture_labeled("Location", text)

    if location:
        location = re.split(
            r"\s+(?:Experience Level|Responsibilities|Required Skills|"
            r"Eligibility|Benefits)\b",
            location,
            maxsplit=1,
            flags=re.IGNORECASE
        )[0]

        location = clean(location)

    # Compact WFO location, e.g. Bengaluru (WFO).
    if not location:
        match = re.search(
            r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})\s*\(WFO\)",
            text
        )
        if match:
            location = match.group(1)

    if location:
        if re.search(r"\binternship\b|\bas per the project\b", location, re.IGNORECASE):
            location = None
    if location:
        assign("location", location)
    elif candidate_location:
        assign("location", candidate_location, "matched_candidate_metadata")

    return result

