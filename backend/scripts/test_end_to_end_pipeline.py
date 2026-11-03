"""Offline end-to-end replay using saved NEXORA discovery datasets."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
DATA_DIR = PROJECT_ROOT / "tests" / "fixtures" / "discovery_runs"

from app.agents.discovery_agent import DiscoveryAgent
from app.agents import opportunity_extraction_agent as extraction_agent
from app.schemas.opportunity import OpportunityExtraction
from app.services import document_extraction_service, llm_service, search_service
from app.services.linkedin_link_service import normalize_job_url
from app.services.listing_parser import extract_linkedin_listings
from scripts import fetch_matched_vacancies


def read_fixture(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def candidate_key(candidate):
    return tuple(
        candidate.get(key, "").casefold().strip()
        for key in ("opportunity_title", "organization", "location")
    )


def test_discovery_and_search_deduplication():
    plan_response = {
        "search_queries": ["paid AI internship India"],
        "target_domains": [],
        "hard_constraints": ["paid"],
        "preferences": [],
        "keywords": ["AI", "internship"],
        "exclusions": [],
        "reasoning": "Find paid AI internships.",
    }
    with patch(
        "app.agents.discovery_agent.generate_structured_output",
        return_value=plan_response,
    ):
        plan = DiscoveryAgent().execute(
            "Find paid AI internships in India; avoid unpaid roles."
        )
    assert "Artificial Intelligence" in plan["target_domains"]
    assert plan["exclusions"] == ["unpaid roles"]

    search_fixture = read_fixture("search_20261031_183533.json")
    assert len(search_fixture["results"]) == 9
    assert len({item["url"] for item in search_fixture["results"]}) == 9

    class FakeDDGS:
        def __init__(self, timeout):
            self.timeout = timeout

        def text(self, query, **kwargs):
            if query == "query failure":
                raise RuntimeError("simulated search timeout")
            return [
                {
                    "href": "https://www.example.org/internship?utm_source=one",
                    "title": "AI Internship",
                    "body": "Paid research internship",
                },
                {
                    "href": "https://example.org/internship?utm_source=two",
                    "title": "AI Internship duplicate",
                    "body": "Duplicate URL from another query",
                },
            ]

    with patch.object(search_service, "DDGS", FakeDDGS):
        search = search_service.search_internships(
            ["query success", "query failure"], max_results_per_query=2
        )
    assert search["total_unique_results"] == 1
    assert search["successful_queries"] == 1
    assert search["failed_queries"] == 1
    assert len(search["results"][0]["matched_queries"]) == 1


def test_listing_link_matching_and_duplicate_handling():
    extracted = read_fixture("extracted_20261101_000834.json")
    listing_occurrences = []
    source_pages_with_text = 0
    fetched_documents = 0
    for record in extracted["records"]:
        document = record.get("document", {})
        fetched_documents += document.get("fetch_status") == "fetched"
        if document.get("extraction_status") == "extracted":
            source_pages_with_text += 1
        url = record.get("search_result", {}).get("url", "")
        if "linkedin.com/jobs/" in url:
            listing_occurrences.extend(
                extract_linkedin_listings(document.get("extracted_text", ""))
            )

    listing_data = read_fixture("listing_candidates_20261101_003424.json")
    keys = [candidate_key(item) for item in listing_data["candidates"]]
    assert len(listing_occurrences) == listing_data["total_candidate_occurrences"]
    assert len(set(keys)) == listing_data["unique_candidate_count"]
    assert listing_data["total_candidate_occurrences"] == 113
    assert listing_data["unique_candidate_count"] == 71

    link_data = read_fixture("linkedin_job_links_20261101_004438.json")
    normalized_links = [
        normalize_job_url(item["job_url"])
        for item in link_data["job_links"]
    ]
    assert len(normalized_links) == 75
    assert all(normalized_links)
    assert len(set(normalized_links)) == len(normalized_links)

    matches = read_fixture("candidate_url_matches_20261101_004907.json")
    assert len(matches["candidate_matches"]) == 62
    assert matches["unique_exact_candidate_matches"] == 56
    assert matches["ambiguous_url_count"] == 2
    assert matches["unmatched_url_count"] == 9
    assert source_pages_with_text == 5
    assert fetched_documents == 5

    # The parser must collapse duplicate listing rows to one candidate.
    duplicate_text = (
        "AI Research Intern AI Research Intern Northstar Labs Bengaluru 2 days ago\n"
        "Northstar Labs\n"
        "AI Research Intern AI Research Intern Northstar Labs Bengaluru 2 days ago\n"
        "Northstar Labs"
    )
    assert len(extract_linkedin_listings(duplicate_text)) == 1


def test_fetch_extraction_failure_and_saved_vacancy_batch():
    vacancies = read_fixture("vacancy_extractions_20261101_005038.json")
    matches = read_fixture("candidate_url_matches_20261101_004907.json")
    exact_matches = {
        item["candidate_id"]: item
        for item in matches["candidate_matches"]
        if item["candidate_match_status"] == "unique_exact_match"
    }
    assert vacancies["batch_size"] == 10
    assert vacancies["successful_fetches"] == 10
    assert vacancies["successful_extractions"] == 10
    assert len(vacancies["results"]) == 10
    for vacancy in vacancies["results"]:
        matched_candidate = exact_matches.get(vacancy["candidate_id"])
        assert matched_candidate is not None
        expected_url = matched_candidate["matched_job_urls"][0]["job_url"]
        actual_url = vacancy.get("matched_job_url") or vacancy.get("final_url")
        assert normalize_job_url(actual_url) == normalize_job_url(expected_url)

    with patch.object(
        document_extraction_service,
        "fetch_document",
        return_value={
            "fetch_status": "fetch_error",
            "document_type": None,
            "final_url": "https://jobs.example.test/internship",
            "error": "simulated connection failure",
        },
    ):
        failed = document_extraction_service.extract_document(
            "https://jobs.example.test/internship"
        )
    assert failed["fetch_status"] == "fetch_error"
    assert failed["extraction_status"] == "not_attempted"
    assert failed["extracted_text"] == ""


def test_resumable_vacancy_batches():
    matches = read_fixture("candidate_url_matches_20261101_004907.json")
    previous_batch = DATA_DIR / "vacancy_extractions_20261101_005038.json"
    completed = fetch_matched_vacancies.completed_vacancy_keys([previous_batch])

    first_batch = fetch_matched_vacancies.select_batch(
        matches["candidate_matches"], batch_size=10
    )
    remaining = fetch_matched_vacancies.select_batch(
        matches["candidate_matches"], batch_size=0, completed=completed
    )
    resumed_batch = fetch_matched_vacancies.select_batch(
        matches["candidate_matches"], batch_size=10, completed=completed
    )
    duplicate_input = matches["candidate_matches"] + [first_batch[0]]
    deduplicated_all = fetch_matched_vacancies.select_batch(
        duplicate_input, batch_size=0
    )

    assert len(first_batch) == 10
    assert len(completed) == 10
    assert len(remaining) == 46
    assert len(resumed_batch) == 10
    assert len(deduplicated_all) == 56
    assert not {
        (candidate["candidate_id"], normalize_job_url(
            candidate["matched_job_urls"][0]["job_url"]
        ))
        for candidate in resumed_batch
    } & completed

    failed_candidate = next(
        item for item in matches["candidate_matches"]
        if item["candidate_match_status"] == "unique_exact_match"
    )
    failed_record = {
        "candidate_id": failed_candidate["candidate_id"],
        "matched_job_url": failed_candidate["matched_job_urls"][0]["job_url"],
        "fetch_status": "fetch_error",
        "extraction_status": "not_attempted",
        "extracted_text": "",
    }
    assert fetch_matched_vacancies.completed_vacancy_key(failed_record) is None
    assert fetch_matched_vacancies.select_batch(
        matches["candidate_matches"], batch_size=1, completed=()
    )[0]["candidate_id"] == failed_candidate["candidate_id"]


def test_all_vacancies_metadata_evidence_and_structured_output():
    vacancy_data = read_fixture("vacancy_extractions_20261101_005038.json")
    records = [
        item for item in vacancy_data["results"]
        if item.get("extraction_status") == "extracted"
        and item.get("extracted_text", "").strip()
    ]
    assert len(records) == 10

    generated = []
    populated_field_count = 0
    evidence_count = 0
    for item in records:
        with patch.object(
            extraction_agent,
            "generate_structured_output",
            return_value={
                "document_kind": "individual_announcement",
                "evidence": [],
            },
        ):
            result = extraction_agent.extract_opportunity(
                source_text=item["extracted_text"],
                source_url=item.get("final_url") or item["matched_job_url"],
                source_title=item["candidate_title"],
                source_type="individual_linkedin_job",
                candidate_metadata={
                    "candidate_id": item["candidate_id"],
                    "candidate_title": item["candidate_title"],
                    "candidate_organization": item["candidate_organization"],
                    "candidate_location": item["candidate_location"],
                },
            )

        output = OpportunityExtraction.model_validate(result["extraction"])
        dumped = output.model_dump()
        assert dumped["opportunity_title"]
        assert dumped["organization"]
        assert result["evidence_validation"]["all_populated_fields_supported"]
        populated_field_count += sum(
            value is not None and value != "" and value != []
            for field, value in dumped.items()
            if field not in {"document_kind", "evidence", "extraction_notes"}
        )
        evidence_count += len(dumped["evidence"])
        for evidence in dumped["evidence"]:
            assert (
                evidence["quote"].casefold()
                in item["extracted_text"].casefold()
                or evidence["source_location"]
                == "Matched vacancy candidate metadata"
            )
        generated.append({
            "candidate_id": item["candidate_id"],
            "job_url": item.get("final_url") or item["matched_job_url"],
            "opportunity": dumped,
        })

    assert len({item["candidate_id"] for item in generated}) == len(generated)
    assert len(generated) == 10
    assert all(item["opportunity"]["organization"] for item in generated)
    print(
        "Replay metrics: 10/10 structured records; "
        f"{populated_field_count} populated fields supported by "
        f"{evidence_count} evidence items."
    )


def test_historical_evidence_quality():
    vacancy_data = read_fixture("vacancy_extractions_20261101_005038.json")
    source_by_candidate = {
        item["candidate_id"]: item.get("extracted_text", "")
        for item in vacancy_data["results"]
    }
    historical = read_fixture(
        "individual_opportunity_extractions_20261103_021257.json"
    )

    before = 0
    after = 0
    for record in historical["records"]:
        extraction_data = record.get("extraction", {})
        before += sum(
            value is not None and value != "" and value != []
            for field, value in extraction_data.items()
            if field not in {"document_kind", "evidence", "extraction_notes"}
        )
        extraction, _ = extraction_agent.validate_and_sanitize_evidence(
            OpportunityExtraction.model_validate(extraction_data),
            source_by_candidate.get(record.get("candidate_id"), ""),
        )
        after += sum(
            value is not None and value != "" and value != []
            for field, value in extraction.model_dump().items()
            if field not in {"document_kind", "evidence", "extraction_notes"}
        )

    assert len(historical["records"]) == 4
    assert before == 11
    assert after == 1
    print(
        "Historical evidence audit: "
        f"{after}/{before} populated fields passed stricter quote/location checks."
    )


def test_llm_fallback():
    calls = []

    def primary(*args):
        calls.append("primary")
        raise RuntimeError("simulated local model outage")

    def fallback(*args):
        calls.append("fallback")
        return {"status": "structured"}

    with (
        patch.object(llm_service, "PRIMARY_PROVIDER", "primary_test"),
        patch.object(llm_service, "FALLBACK_PROVIDER", "fallback_test"),
        patch.dict(
            llm_service.PROVIDERS,
            {"primary_test": primary, "fallback_test": fallback},
        ),
    ):
        result = llm_service.generate_structured_output("system", "user", {})

    assert result == {"status": "structured"}
    assert calls == ["primary", "fallback"]

    def failing_fallback(*args):
        raise RuntimeError("simulated fallback outage")

    with (
        patch.object(llm_service, "PRIMARY_PROVIDER", "primary_test"),
        patch.object(llm_service, "FALLBACK_PROVIDER", "fallback_test"),
        patch.dict(
            llm_service.PROVIDERS,
            {"primary_test": primary, "fallback_test": failing_fallback},
        ),
    ):
        try:
            llm_service.generate_structured_output("system", "user", {})
        except RuntimeError as error:
            assert "Both LLM providers failed" in str(error)
        else:
            raise AssertionError("Expected both-provider failure to propagate")


def main():
    tests = [
        test_discovery_and_search_deduplication,
        test_listing_link_matching_and_duplicate_handling,
        test_fetch_extraction_failure_and_saved_vacancy_batch,
        test_resumable_vacancy_batches,
        test_all_vacancies_metadata_evidence_and_structured_output,
        test_historical_evidence_quality,
        test_llm_fallback,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} offline end-to-end stage groups")


if __name__ == "__main__":
    main()
