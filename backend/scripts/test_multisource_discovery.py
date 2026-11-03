"""Offline regression checks for modular sources and evidence-based review."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.source_adapters import SOURCE_ADAPTERS, build_source_queries, source_for_url
from app.services.verification_service import assess_verification


def test_all_requested_sources_have_adapters():
    keys = {adapter.key for adapter in SOURCE_ADAPTERS}
    assert keys == {
        "government", "research", "universities", "company_careers",
        "internshala", "indeed", "naukri", "foundit", "wellfound", "linkedin",
    }
    queries = build_source_queries("AI internship India")
    assert len(queries) == len(SOURCE_ADAPTERS)
    assert all("AI internship India" in item["query"] for item in queries)


def test_platform_and_official_source_classification():
    assert source_for_url("https://in.indeed.com/viewjob?jk=1")["adapter"] == "indeed"
    assert source_for_url("https://lab.gov.in/internships")["source_type"] == "government_domain"
    assert source_for_url("https://university.ac.in/jobs")["source_type"] == "academic_domain"
    assert source_for_url("https://example.test/careers/ai-intern")["adapter"] == "company_careers"


def test_fraud_flags_require_and_preserve_source_evidence():
    record = {
        "source": {"url": "https://jobs.example.test/role"},
        "extraction": {"organization": "Northstar Labs", "opportunity_title": "AI Intern"},
    }
    clean = assess_verification(record, source_text="Applications close on 30 June.")
    assert clean["fraud_risk"]["level"] == "unknown"
    flagged = assess_verification(
        record,
        source_text="Pay a registration fee to guarantee your internship selection. Apply via WhatsApp.",
    )
    assert flagged["fraud_risk"]["level"] == "elevated_review"
    assert {item["signal"] for item in flagged["fraud_risk"]["signals"]} >= {
        "upfront_fee", "guaranteed_selection", "unofficial_messaging_application"
    }
    assert all(item["quote"] and item["source_url"] == record["source"]["url"]
               for item in flagged["fraud_risk"]["signals"])
    assert flagged["fraud_risk"]["is_authenticity_verdict"] is False


def test_employer_verification_requires_matching_official_source():
    record = {
        "source": {"url": "https://jobs.example.test/role"},
        "extraction": {"organization": "Northstar Labs", "opportunity_title": "AI Intern"},
    }
    result = assess_verification(record, corroborating_sources=[{
        "url": "https://northstarlabs.com/careers/ai-intern",
        "organization": "Northstar Labs",
        "title": "AI Intern",
    }])
    assert result["verification_status"] == "independently_corroborated"
    unrelated = assess_verification(record, corroborating_sources=[{
        "url": "https://different.example.test/role",
        "organization": "Northstar Labs",
        "title": "AI Intern",
    }])
    assert unrelated["verification_status"] == "not_independently_verified"


def main():
    test_all_requested_sources_have_adapters()
    print("PASS: all requested source families have modular search adapters")
    test_platform_and_official_source_classification()
    print("PASS: source hosts are classified without treating job boards as official")
    test_fraud_flags_require_and_preserve_source_evidence()
    print("PASS: fraud indicators retain quotations and do not claim an authenticity verdict")
    test_employer_verification_requires_matching_official_source()
    print("PASS: employer corroboration requires a distinct matching official source")


if __name__ == "__main__":
    main()
