"""Cross-source verification and API result assembly for one workflow run."""

from app.services.verification_service import assess_verification
from app.services.workflow_document_processor import WorkflowDocumentProcessor
from app.services.workflow_matching import corroborating_records


def build_workflow_result(plan, source_queries, search_report,
                          processor: WorkflowDocumentProcessor):
    for record in processor.output_records:
        if not record.get("ranking"):
            continue
        verification = assess_verification(
            record,
            corroborating_sources=corroborating_records(
                processor.output_records, record
            ),
        )
        prior_risk = record.get("verification", {}).get("fraud_risk")
        if prior_risk:
            verification["fraud_risk"] = prior_risk
        record["verification_status"] = verification["verification_status"]
        record["verification"] = verification
        record["opportunity_id"] = processor.store.save_opportunity(record)

    ranked = sorted(
        (item for item in processor.output_records if item.get("ranking")),
        key=lambda item: item["ranking"]["score"],
        reverse=True,
    )
    non_individual = [item for item in processor.output_records if not item.get("ranking")]
    return {
        "plan": plan,
        "discovery_candidates": search_report.get("results", []),
        "retrieved_documents": processor.retrieved_documents,
        "search": {
            key: value for key, value in search_report.items()
            if key != "results"
        },
        "summary": {
            "sources_discovered": search_report.get("total_unique_results", 0),
            "source_adapters_queried": [item["adapter"] for item in source_queries],
            "vacancy_pages_attempted": processor.attempted_documents,
            "individual_opportunities_extracted": len(ranked),
            "listing_candidates_needing_url_review": len(processor.listing_match_review),
            "non_individual_records": len(non_individual),
            "login_wall_records": sum(
                item.get("record_status") == "source_login_wall"
                for item in non_individual
            ),
            "records_needing_review": sum(
                item.get("record_status") == "needs_human_review"
                or item.get("eligibility", {}).get("status") == "needs_review"
                for item in ranked
            ),
            "failures": len(processor.errors),
        },
        "opportunities": ranked,
        "url_match_review": processor.listing_match_review,
        "non_individual_sources": non_individual,
        "errors": processor.errors,
        "agent_runs": processor.agent_runs,
    }
