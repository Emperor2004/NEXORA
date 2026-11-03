"""Pure matching helpers used by the discovery workflow."""

import re
from urllib.parse import unquote


def normalize_identity(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())


def employer_slug(url):
    segment = unquote(url.rstrip("/").split("/")[-1])
    match = re.search(r"-at-(.+)-\d{6,}$", segment)
    return normalize_identity(match.group(1)) if match else ""


def match_listing_candidates(candidates, links):
    matched = []
    review = []
    for candidate in candidates:
        title = normalize_identity(candidate.get("opportunity_title"))
        organization = normalize_identity(candidate.get("organization"))
        hits = [
            link for link in links
            if normalize_identity(link.get("anchor_text")) == title
            and employer_slug(link.get("job_url", "")) == organization
        ]
        if len(hits) == 1:
            matched.append((candidate, hits[0]))
        else:
            review.append({
                "candidate": candidate,
                "status": "no_exact_match" if not hits else "ambiguous_match",
                "matched_url_count": len(hits),
            })
    return matched, review


def identity_for(extraction, fallback=""):
    parts = tuple(normalize_identity(extraction.get(field)) for field in (
        "opportunity_title", "organization", "location"
    ))
    return "|".join(parts) if all(parts[:2]) else fallback


def corroborating_records(records, selected_record):
    corroborating = []
    for record in records:
        if record is selected_record:
            continue
        extraction = record.get("extraction", {})
        corroborating.append({
            "url": record.get("source", {}).get("final_url")
                   or record.get("source", {}).get("url", ""),
            "organization": extraction.get("organization"),
            "title": extraction.get("opportunity_title"),
        })
        corroborating.extend({
            "url": source.get("url", ""),
            "organization": extraction.get("organization"),
            "title": extraction.get("opportunity_title"),
        } for source in record.get("source_records", []))
    return corroborating
