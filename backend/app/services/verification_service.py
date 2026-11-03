"""Conservative, explainable source and fraud-risk assessment."""

import re
from urllib.parse import urlsplit

from app.services.source_adapters import source_for_url


FRAUD_SIGNALS = (
    ("upfront_fee", re.compile(r"\b(?:pay|send|deposit)\b.{0,50}\b(?:fee|money|payment|deposit)\b|\bregistration fee\b", re.I)),
    ("guaranteed_selection", re.compile(r"\bguarantee(?:d)?\b.{0,50}\b(?:job|internship|selection|placement)\b", re.I)),
    ("personal_payment_channel", re.compile(r"\b(?:UPI|personal bank account|gift card|crypto(?:currency)?)\b", re.I)),
    ("unofficial_messaging_application", re.compile(r"(?:\b(?:WhatsApp|Telegram)\b.{0,50}\b(?:apply|recruit|contact|send)\b|\b(?:apply|recruit|contact|send)\b.{0,50}\b(?:WhatsApp|Telegram)\b)", re.I)),
    ("unverifiable_email_domain", re.compile(r"\b[A-Z0-9._%+-]+@(?![A-Z0-9.-]+\.(?:com|org|edu|gov|in)\b)[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
)


def _norm(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())


def assess_verification(record: dict, corroborating_sources=None, source_text="") -> dict:
    """Report provenance and corroboration; never claim authenticity from a fetch."""
    source = record.get("source", {})
    url = source.get("final_url") or source.get("url") or ""
    kind = source_for_url(url)
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    org = _norm(record.get("extraction", {}).get("organization"))
    title = _norm(record.get("extraction", {}).get("opportunity_title"))
    corroboration = []
    for candidate in corroborating_sources or []:
        other_url = candidate.get("url", "")
        other_org = _norm(candidate.get("organization"))
        other_title = _norm(candidate.get("title"))
        other_host = (urlsplit(other_url).hostname or "").lower().removeprefix("www.")
        official_other = (
            other_host.endswith((".gov.in", ".nic.in", ".ac.in", ".edu.in"))
            or bool(other_org and other_org in _norm(other_host))
        )
        if (official_other and other_host and other_host != host and org and title
                and other_org == org and other_title == title):
            corroboration.append({"url": other_url, "organization_match": True, "title_match": True})

    official_domain = kind["source_type"] in {"government_domain", "academic_domain"}
    organization_in_host = bool(org and (org in _norm(host) or _norm(host) in org))
    if official_domain or (kind["adapter"] == "web" and organization_in_host):
        status = "official_source_unverified_employer"
        reason = "The posting is hosted on a government, academic, or organization-matching domain; vacancy validity and employer identity are still unconfirmed."
    elif corroboration:
        status = "independently_corroborated"
        reason = "A separate host reports a matching employer and opportunity title."
    else:
        status = "not_independently_verified"
        reason = "No independent source confirming this employer and vacancy was supplied."

    text = source_text or ""
    risk_evidence = []
    for signal, pattern in FRAUD_SIGNALS:
        match = pattern.search(text)
        if match:
            quote = text[max(0, match.start() - 60):min(len(text), match.end() + 60)].strip()
            risk_evidence.append({"signal": signal, "quote": quote, "source_url": url})
    if risk_evidence:
        risk_level = "elevated_review"
    elif status == "not_independently_verified":
        risk_level = "unknown"
    else:
        risk_level = "no_flag_detected"
    return {
        "verification_status": status,
        "verification_reason": reason,
        "employer_domain": host,
        "source_adapter": kind["adapter"],
        "independent_sources": corroboration,
        "fraud_risk": {"level": risk_level, "signals": risk_evidence,
                        "method": "evidence_phrase_rules", "is_authenticity_verdict": False},
    }
