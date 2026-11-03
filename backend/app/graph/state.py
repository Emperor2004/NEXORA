from typing import Any, TypedDict


class NexoraWorkflowState(TypedDict, total=False):
    """Shared, inspectable state for one bounded NEXORA workflow run."""

    workflow_id: str
    user_request: str
    candidate_profile_ref: str | None
    candidate_profile: dict[str, Any] | None
    max_results: int
    discovery_plan: dict[str, Any] | None
    discovery_candidates: list[dict[str, Any]]
    resolved_opportunities: list[dict[str, Any]]
    retrieved_documents: list[dict[str, Any]]
    extracted_opportunities: list[dict[str, Any]]
    verification_reports: list[dict[str, Any]]
    eligibility_assessments: list[dict[str, Any]]
    rankings: list[dict[str, Any]]
    application_drafts: list[dict[str, Any]]
    application_events: list[dict[str, Any]]
    review_queue: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    agent_runs: list[dict[str, Any]]
    workflow_result: dict[str, Any]
    workflow_status: str
    created_at: str
    updated_at: str


class DiscoveryState(TypedDict, total=False):
    """Compatibility state for the existing discovery-plan endpoint."""

    workflow_id: str
    user_request: str
    plan: dict[str, Any]
    error: str
    workflow_status: str
    agent_runs: list[dict[str, Any]]
    discovery_plan: dict[str, Any]
    created_at: str
    updated_at: str
