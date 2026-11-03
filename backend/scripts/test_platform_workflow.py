import json
import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app
from app.services.eligibility_service import assess_eligibility
from app.services.internship_workflow_service import (
    InternshipWorkflow,
    _match_listing_candidates,
)
from app.services.opportunity_store import LocalOpportunityStore, SCHEMA_VERSION
from app.services.ranking_service import rank_opportunity


TEST_DB = PROJECT_ROOT / ".test_nexora_workflow.sqlite3"


def clean_test_db():
    for suffix in ("", "-shm", "-wal"):
        Path(str(TEST_DB) + suffix).unlink(missing_ok=True)


def database_version():
    connection = sqlite3.connect(TEST_DB)
    try:
        return connection.execute("PRAGMA user_version").fetchone()[0]
    finally:
        connection.close()


def sample_record():
    return {
        "source": {
            "url": "https://www.linkedin.com/jobs/view/123456",
            "title": "AI Research Intern",
        },
        "classification": {
            "document_kind": "individual_announcement",
            "reason": "fixture",
        },
        "record_status": "candidate_for_human_review",
        "verification_status": "not_independently_verified",
        "extraction": {
            "document_kind": "individual_announcement",
            "opportunity_title": "AI Research Intern",
            "organization": "Northstar Labs",
            "location": "Remote",
            "eligible_degrees": ["B.Tech"],
            "eligible_branches": ["Computer Science and Engineering"],
            "eligible_years": ["3rd year"],
            "minimum_cgpa": "8.0",
            "nationality_requirement": "Indian",
            "research_areas": ["Artificial Intelligence"],
            "required_skills": ["Python"],
            "is_paid": None,
            "stipend": None,
            "duration": "3 months",
            "application_deadline": None,
            "application_url": None,
            "evidence": [
                {"field_name": "eligible_degrees", "source_location": "Eligibility", "quote": "B.Tech"},
                {"field_name": "eligible_branches", "source_location": "Eligibility", "quote": "Computer Science and Engineering"},
                {"field_name": "eligible_years", "source_location": "Eligibility", "quote": "3rd year"},
                {"field_name": "minimum_cgpa", "source_location": "Eligibility", "quote": "Minimum CGPA: 8.0"},
                {"field_name": "nationality_requirement", "source_location": "Eligibility", "quote": "Indian citizens"},
            ],
        },
        "evidence_validation": {
            "all_populated_fields_supported": True,
            "field_validation": {
                field: {"status": "supported_by_source_quote"}
                for field in (
                    "opportunity_title", "organization", "location",
                    "eligible_degrees", "eligible_branches", "eligible_years",
                    "minimum_cgpa", "nationality_requirement", "duration",
                )
            },
        },
    }


def test_eligibility_and_ranking():
    record = sample_record()
    profile = {
        "degrees": ["Bachelor of Technology"],
        "branches": ["CSE"],
        "academic_years": ["3rd year"],
        "cgpa": 8.4,
        "nationality": "India",
        "target_domains": ["Artificial Intelligence"],
        "preferred_locations": ["Remote"],
    }
    eligible = assess_eligibility(record, profile)
    assert eligible["status"] == "eligible"
    assert len(eligible["evaluated_fields"]) == 5

    low_gpa = assess_eligibility(record, {**profile, "cgpa": 7.2})
    assert low_gpa["status"] == "ineligible"
    missing_profile = assess_eligibility(record, None)
    assert missing_profile["status"] == "needs_review"
    rejected_requirement = {
        **record,
        "evidence_validation": {
            **record["evidence_validation"],
            "unsupported_fields": ["eligible_years"],
        },
    }
    assert assess_eligibility(rejected_requirement, profile)["status"] == "needs_review"

    record["eligibility"] = eligible
    ranking = rank_opportunity(record, profile)
    assert 0 <= ranking["score"] <= 100
    assert [factor["name"] for factor in ranking["factors"]] == [
        "eligibility", "target_relevance", "location_fit",
        "evidence_coverage", "field_completeness"
    ]
    assert ranking["score"] > rank_opportunity(
        {**record, "eligibility": low_gpa}, profile
    )["score"]


def test_end_to_end_workflow_and_local_tracking():
    clean_test_db()
    try:
        store = LocalOpportunityStore(TEST_DB)
        assert database_version() == SCHEMA_VERSION
        workflow = InternshipWorkflow(store=store)
        source_text = (
            "Job Title: AI Research Intern Company: Northstar Labs Location: Remote "
            "Duration: 3 months Eligibility: B.Tech, Computer Science and Engineering, "
            "3rd year, Minimum CGPA: 8.0, Indian citizens"
        )
        llm_output = {
            "document_kind": "individual_announcement",
            "eligible_degrees": ["B.Tech"],
            "eligible_branches": ["Computer Science and Engineering"],
            "eligible_years": ["3rd year"],
            "minimum_cgpa": "8.0",
            "nationality_requirement": "Indian",
            "evidence": [
                {"field_name": "eligible_degrees", "source_location": "Eligibility", "quote": "B.Tech"},
                {"field_name": "eligible_branches", "source_location": "Eligibility", "quote": "Computer Science and Engineering"},
                {"field_name": "eligible_years", "source_location": "Eligibility", "quote": "3rd year"},
                {"field_name": "minimum_cgpa", "source_location": "Eligibility", "quote": "Minimum CGPA: 8.0"},
                {"field_name": "nationality_requirement", "source_location": "Eligibility", "quote": "Indian citizens"},
            ],
        }
        search_report = {
            "total_unique_results": 2,
            "queries_executed": 1,
            "successful_queries": 1,
            "failed_queries": 0,
            "errors": [],
            "results": [
                {
                    "title": "Search title may be noisy",
                    "url": "https://www.linkedin.com/jobs/view/123456",
                    "source_type": "other_domain",
                },
                {
                    "title": "Duplicate result",
                    "url": "https://linkedin.com/jobs/view/123456?utm_source=test",
                    "source_type": "other_domain",
                },
            ],
        }
        plan = {
            "search_queries": ["AI research internship"],
            "target_domains": ["Artificial Intelligence"],
            "hard_constraints": [], "preferences": [], "keywords": [],
            "exclusions": [], "reasoning": "fixture plan",
        }
        with (
            patch("app.services.internship_workflow_service.DiscoveryAgent.execute", return_value=plan),
            patch("app.services.internship_workflow_service.search_internships", return_value=search_report),
            patch("app.services.internship_workflow_service.extract_document", return_value={
                "fetch_status": "fetched",
                "extraction_status": "extracted",
                "document_type": "html",
                "final_url": "https://www.linkedin.com/jobs/view/123456",
                "extracted_text": source_text,
            }),
            patch("app.agents.opportunity_extraction_agent.generate_structured_output", return_value=llm_output),
        ):
            result = workflow.run(
                "Find AI research internships",
                candidate_profile={
                    "degrees": ["Bachelor of Technology"],
                    "branches": ["CSE"],
                    "academic_years": ["3rd year"],
                    "cgpa": 8.4,
                    "nationality": "India",
                    "target_domains": ["Artificial Intelligence"],
                },
                max_results=5,
            )

        assert result["summary"]["individual_opportunities_extracted"] == 1
        opportunity = result["opportunities"][0]
        assert opportunity["eligibility"]["status"] == "eligible"
        assert opportunity["verification_status"] == "not_independently_verified"
        opportunity_id = opportunity["opportunity_id"]
        assert len(store.list_opportunities()) == 1
        assert store.get_opportunity(opportunity_id)["extraction"]["organization"] == "Northstar Labs"

        application = store.create_application(opportunity_id, notes="Tailor the resume")
        assert application["status"] == "interested"
        duplicate_application = store.create_application(
            opportunity_id, notes="Do not create a second application"
        )
        assert duplicate_application["id"] == application["id"]

        restarted_store = LocalOpportunityStore(TEST_DB)
        assert len(restarted_store.list_opportunities()) == 1
        assert restarted_store.get_application(application["id"])["status"] == "interested"

        with patch.dict(os.environ, {"NEXORA_API_TOKEN": ""}):
            unauthenticated_client = TestClient(app)
            assert unauthenticated_client.get("/api/opportunities").status_code == 403

        with patch.dict(os.environ, {
            "NEXORA_DB_PATH": str(TEST_DB),
            "NEXORA_API_TOKEN": "test-token",
        }):
            client = TestClient(
                app, headers={"Authorization": "Bearer test-token"}
            )
            assert TestClient(app).get("/api/opportunities").status_code == 401
            with patch("app.main.InternshipWorkflow") as workflow_class:
                workflow_class.return_value.run.return_value = {
                    "summary": {"individual_opportunities_extracted": 1},
                    "opportunities": [],
                }
                workflow_response = client.post("/api/workflow/run", json={
                    "user_request": "Find AI research internships",
                    "max_results": 3,
                    "candidate_profile": {"degrees": ["B.Tech"], "cgpa": 8.2},
                })
                assert workflow_response.status_code == 200
                assert workflow_class.return_value.run.call_args.kwargs[
                    "candidate_profile"
                ]["cgpa"] == 8.2
            invalid_workflow_request = client.post("/api/workflow/run", json={
                "user_request": "Find AI research internships",
                "max_results": 100,
            })
            assert invalid_workflow_request.status_code == 422
            response = client.get(f"/api/opportunities/{opportunity_id}")
            assert response.status_code == 200
            checklist = client.get(
                f"/api/opportunities/{opportunity_id}/application-checklist"
            )
            assert checklist.status_code == 200
            assert checklist.json()["automated_submission"] is False
            api_created = client.post("/api/applications", json={
                "opportunity_id": opportunity_id,
                "notes": "Review eligibility before applying",
            })
            assert api_created.status_code == 201
            api_application_id = api_created.json()["id"]
            preparing = client.patch(
                f"/api/applications/{api_application_id}",
                json={"status": "preparing", "note": "Drafting materials"},
            )
            assert preparing.status_code == 200
            submitted = client.patch(
                f"/api/applications/{api_application_id}",
                json={"status": "submitted", "note": "Submitted manually"},
            )
            assert submitted.status_code == 200
            assert submitted.json()["notes"] == "Submitted manually"
            assert [
                event["new_status"] for event in submitted.json()["history"]
            ] == ["interested", "preparing", "submitted"]
            invalid_transition = client.patch(
                f"/api/applications/{api_application_id}",
                json={"status": "interested"},
            )
            assert invalid_transition.status_code == 409
            listing = client.get("/api/applications")
            assert listing.status_code == 200
            assert len(listing.json()["applications"]) == 1

        connection = sqlite3.connect(TEST_DB)
        try:
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
            connection.commit()
        finally:
            connection.close()
        try:
            LocalOpportunityStore(TEST_DB)
        except RuntimeError as error:
            assert "newer than supported" in str(error)
        else:
            raise AssertionError("Newer database schema was silently accepted")
    finally:
        clean_test_db()


def test_workflow_failure_budget():
    class NoWriteStore:
        def save_opportunity(self, record):
            raise AssertionError("Failed fetch must not write an opportunity")

    search_report = {
        "total_unique_results": 3,
        "queries_executed": 1,
        "successful_queries": 1,
        "failed_queries": 0,
        "errors": [],
        "results": [
            {
                "title": f"AI internship {index}",
                "url": f"https://jobs.example.test/internship/{index}",
                "source_type": "other_domain",
            }
            for index in range(3)
        ],
    }
    plan = {
        "search_queries": ["AI internships"],
        "target_domains": ["Artificial Intelligence"],
    }
    workflow = InternshipWorkflow(store=NoWriteStore())
    with (
        patch("app.services.internship_workflow_service.DiscoveryAgent.execute", return_value=plan),
        patch("app.services.internship_workflow_service.search_internships", return_value=search_report),
        patch("app.services.internship_workflow_service.extract_document", return_value={
            "fetch_status": "fetch_error",
            "extraction_status": "not_attempted",
            "extracted_text": "",
            "error": "simulated failure",
        }) as fetch,
    ):
        result = workflow.run("Find AI internships", max_results=2)

    assert fetch.call_count == 2
    assert result["summary"]["vacancy_pages_attempted"] == 2
    assert result["summary"]["failures"] == 2
    assert result["opportunities"] == []


def test_listing_match_review_states():
    candidates = [
        {
            "opportunity_title": "AI Research Intern",
            "organization": "Northstar Labs",
            "location": "Remote",
        },
        {
            "opportunity_title": "Data Science Intern",
            "organization": "Unknown Company",
            "location": "India",
        },
    ]
    links = [
        {
            "anchor_text": "AI Research Intern",
            "job_url": "https://www.linkedin.com/jobs/view/ai-research-intern-at-northstar-labs-123456",
        },
        {
            "anchor_text": "AI Research Intern",
            "job_url": "https://www.linkedin.com/jobs/view/ai-research-intern-at-northstar-labs-654321",
        },
    ]
    matched, review = _match_listing_candidates(candidates, links)
    assert not matched
    assert [item["status"] for item in review] == [
        "ambiguous_match", "no_exact_match"
    ]


def main():
    test_eligibility_and_ranking()
    print("PASS: conservative eligibility decisions and explainable ranking")
    test_end_to_end_workflow_and_local_tracking()
    print("PASS: discovery-to-tracking workflow, local persistence, and API")
    test_workflow_failure_budget()
    print("PASS: failed records do not exceed the configured cost cap")
    test_listing_match_review_states()
    print("PASS: unresolved listing URLs are surfaced for review")


if __name__ == "__main__":
    main()
