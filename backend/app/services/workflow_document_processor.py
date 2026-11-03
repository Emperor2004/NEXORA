"""Retrieve and process one discovered vacancy page."""

from app.agents.opportunity_extraction_agent import extract_opportunity
from app.agents.registry import get_agent_profile
from app.services.agent_runtime import create_agent_task, run_agent_task
from app.services.document_extraction_service import extract_document
from app.services.eligibility_service import assess_eligibility
from app.services.opportunity_store import LocalOpportunityStore
from app.services.ranking_service import rank_opportunity
from app.services.search_service import normalize_url
from app.services.verification_service import assess_verification
from app.services.workflow_matching import identity_for


class WorkflowDocumentProcessor:
    """Own mutable per-run document state and vacancy-level processing."""

    def __init__(self, *, workflow_id, candidate_profile, max_results,
                 parent_task_id=None, store=None):
        self.workflow_id = workflow_id
        self.candidate_profile = candidate_profile
        self.max_results = max_results
        self.parent_task_id = parent_task_id
        self.store = store or LocalOpportunityStore()
        self.agent_runs = []
        self.output_records = []
        self.errors = []
        self.retrieved_documents = []
        self.listing_match_review = []
        self.seen_sources = set()
        self.attempted_urls = set()
        self.seen_opportunities = set()
        self.attempted_documents = 0

    def process(self, url, title, source_type, *, candidate_metadata=None,
                discovery_result=None):
        key = normalize_url(url)
        if key and key in self.attempted_urls:
            return False
        if self.attempted_documents >= self.max_results:
            return False

        self.attempted_documents += 1
        if key:
            self.attempted_urls.add(key)
        try:
            document = extract_document(url)
            self.retrieved_documents.append({
                "requested_url": url,
                "final_url": document.get("final_url"),
                "fetch_status": document.get("fetch_status"),
                "extraction_status": document.get("extraction_status"),
                "characters_extracted": len(document.get("extracted_text", "")),
            })
            if (document.get("extraction_status") != "extracted"
                    or not document.get("extracted_text", "").strip()):
                self.errors.append({
                    "stage": "fetch_or_text_extraction",
                    "url": url,
                    "error": document.get("error") or document.get("fetch_status"),
                })
                return False

            extractor_profile = get_agent_profile("opportunity_extractor")
            source_url = document.get("final_url") or url
            task = create_agent_task(
                "opportunity_extractor",
                self.workflow_id,
                {
                    "source_text": document["extracted_text"],
                    "source_url": source_url,
                    "source_title": title,
                    "source_type": source_type,
                    "candidate_metadata": candidate_metadata,
                },
                parent_task_id=self.parent_task_id,
                input_reference_ids=[source_url],
                privacy_classification="public_source_content",
            )
            result = run_agent_task(
                task,
                lambda payload: extract_opportunity(
                    **payload,
                    timeout_seconds=extractor_profile.timeout_seconds,
                    max_output_tokens=extractor_profile.max_output_tokens,
                    allowed_providers=extractor_profile.allowed_providers,
                ),
            )
            self.agent_runs.append(result.model_dump(mode="json"))
            if result.status != "succeeded":
                raise RuntimeError("Opportunity extraction agent did not return a valid record.")
            record = result.structured_output
            discovery = discovery_result or {}
            record["source"].update({
                "requested_url": url,
                "final_url": document.get("final_url"),
                "fetch_status": document.get("fetch_status"),
                "extraction_status": document.get("extraction_status"),
                "original_source_url": url,
                "discovery_source": {
                    "adapter": discovery.get("source_adapter", "unknown"),
                    "search_result_url": discovery.get("original_source_url", url),
                    "search_result_title": discovery.get("title", title),
                },
            })

            if record.get("extraction", {}).get("document_kind") != "individual_announcement":
                self.output_records.append(record)
                return False

            identity = identity_for(record["extraction"], key)
            if identity in self.seen_opportunities:
                self._add_duplicate_source(identity, url, discovery)
                return False

            self.seen_opportunities.add(identity)
            verification = assess_verification(
                record, source_text=document.get("extracted_text", "")
            )
            record["verification_status"] = verification["verification_status"]
            record["verification"] = verification
            record["eligibility"] = assess_eligibility(record, self.candidate_profile)
            record["ranking"] = rank_opportunity(record, self.candidate_profile)
            record["opportunity_id"] = self.store.save_opportunity(record)
            self.output_records.append(record)
            return True
        except Exception as error:
            self.errors.append({
                "stage": "verify_extract_assess_rank",
                "url": url,
                "error": f"{type(error).__name__}: {str(error)[:500]}",
            })
            return False

    def _add_duplicate_source(self, identity, url, discovery):
        for existing in self.output_records:
            if identity_for(existing.get("extraction", {})) != identity:
                continue
            sources = existing.setdefault("source_records", [])
            sources.append({
                "url": url,
                "adapter": discovery.get("source_adapter", "unknown"),
            })
            self.store.save_opportunity(existing)
            return
