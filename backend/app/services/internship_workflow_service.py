"""Public workflow facade; coordinates small single-purpose services."""

from uuid import uuid4

from app.services.opportunity_store import LocalOpportunityStore
from app.services.search_service import search_internships
from app.services.workflow_document_processor import WorkflowDocumentProcessor
from app.services.workflow_matching import match_listing_candidates
from app.services.workflow_result_builder import build_workflow_result
from app.services.workflow_source_resolver import resolve_search_results
from app.services.workflow_planner import MAX_SEARCH_QUERIES, plan_discovery


MAX_RESULTS_PER_QUERY = 3

# Keep this private-name alias for existing callers and regression fixtures.
_match_listing_candidates = match_listing_candidates


class InternshipWorkflow:
    """Bounded orchestration over planning, source resolution, and processing."""

    def __init__(self, store=None):
        self.store = store or LocalOpportunityStore()

    def run(self, user_request, candidate_profile=None, max_results=5,
            workflow_id=None, parent_task_id=None):
        if not 1 <= max_results <= 10:
            raise ValueError("max_results must be between 1 and 10")

        workflow_id = workflow_id or str(uuid4())
        plan, source_queries, queries, planner_run = plan_discovery(
            user_request, workflow_id, parent_task_id
        )
        search_report = search_internships(
            queries=queries,
            max_results_per_query=MAX_RESULTS_PER_QUERY,
        )
        processor = WorkflowDocumentProcessor(
            workflow_id=workflow_id,
            candidate_profile=candidate_profile,
            max_results=max_results,
            parent_task_id=parent_task_id,
            store=self.store,
        )
        processor.agent_runs.insert(0, planner_run)
        resolve_search_results(search_report.get("results", []), processor)
        return build_workflow_result(
            plan, source_queries, search_report, processor
        )
