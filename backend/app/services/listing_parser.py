
import re
from urllib.parse import urljoin, urlparse


POSTING_AGE_RE = re.compile(
    r"(?P<age>(?:\d+\s+(?:minute|hour|day|week|month|year)s?\s+ago|"
    r"just now|today|yesterday))\s*$",
    re.IGNORECASE
)


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def split_repeated_title(prefix: str):
    """
    Remove an exact repeated title.

    Example:
        Data Science Intern Data Science Intern

    Returns:
        ("Data Science Intern", "")

    If the title is not duplicated, returns the complete prefix.
    """
    prefix = normalize_space(prefix)
    tokens = prefix.split()

    if len(tokens) >= 2 and len(tokens) % 2 == 0:
        midpoint = len(tokens) // 2
        first = tokens[:midpoint]
        second = tokens[midpoint:]

        if first == second:
            return " ".join(first), ""

    return prefix, ""


def make_candidate(title, company, location, posting_age, row, line_number):
    title = normalize_space(title)
    company = normalize_space(company)
    location = normalize_space(location)

    if not title or not company or not location:
        return None

    if len(title) < 3:
        return None

    return {
        "opportunity_title": title,
        "organization": company,
        "location": location,
        "posting_age": posting_age,
        "duration": None,
        "application_url": None,
        "source_type": "job_board_listing",
        "discovery_status": "unverified_candidate",
        "eligibility_status": "not_assessed",
        "verification_status": "not_verified",
        "source_location": f"Extracted text row {line_number}",
        "source_excerpt": row
    }


def extract_combined_row(lines, index, age_match):
    """
    Parse LinkedIn's combined-row layout.

    Example:
        Data Science Intern Data Science Intern Sony Research India
        Bengaluru, Karnataka, India 3 weeks ago

        Sony Research India
    """
    row = lines[index]

    if index + 1 >= len(lines):
        return None

    company = lines[index + 1]
    without_age = row[:age_match.start()].strip()

    company_position = without_age.rfind(company)

    if company_position <= 0:
        return None

    prefix = without_age[:company_position].strip()
    suffix = without_age[
        company_position + len(company):
    ].strip()

    location = suffix.strip(" |,-")

    if not location:
        return None

    title, remainder = split_repeated_title(prefix)

    if remainder:
        return None

    return make_candidate(
        title=title,
        company=company,
        location=location,
        posting_age=age_match.group("age"),
        row=row,
        line_number=index + 1
    )


def extract_legacy_layout(lines, index, age_match):
    """
    Support the earlier multiline layout.

    Example:
        Data Science Intern
        Sony Research India
        Bengaluru, Karnataka, India
        3 weeks ago
    """
    if index < 3:
        return None

    title = lines[index - 3]
    company = lines[index - 2]
    location = lines[index - 1]
    row = " | ".join(lines[index - 3:index + 1])

    return make_candidate(
        title=title,
        company=company,
        location=location,
        posting_age=age_match.group("age"),
        row=row,
        line_number=index + 1
    )


def extract_linkedin_listings(source_text: str) -> list[dict]:
    lines = [
        normalize_space(line)
        for line in source_text.splitlines()
        if normalize_space(line)
    ]

    candidates = []
    seen = set()

    for index, row in enumerate(lines):
        age_match = POSTING_AGE_RE.search(row)

        if not age_match:
            continue

        # First try the actual LinkedIn combined-row structure.
        candidate = extract_combined_row(
            lines,
            index,
            age_match
        )

        # Fall back to the older multiline structure.
        if candidate is None:
            candidate = extract_legacy_layout(
                lines,
                index,
                age_match
            )

        if candidate is None:
            continue

        key = (
            candidate["opportunity_title"].casefold(),
            candidate["organization"].casefold(),
            candidate["location"].casefold()
        )

        if key in seen:
            continue

        seen.add(key)
        candidates.append(candidate)

    return candidates


def extract_html_job_links(html: str, base_url: str) -> list[dict]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen = set()

    for anchor in soup.find_all("a", href=True):
        href = urljoin(base_url, anchor["href"])
        title = normalize_space(
            anchor.get_text(" ", strip=True)
        )

        if not title or len(title) < 5:
            continue

        parsed = urlparse(href)

        if parsed.scheme not in {"http", "https"}:
            continue

        if "linkedin.com/jobs/view/" not in href:
            continue

        if href in seen:
            continue

        seen.add(href)

        results.append({
            "opportunity_title": title,
            "application_url": href,
            "source_type": "job_board_listing",
            "discovery_status": "unverified_candidate"
        })

    return results
