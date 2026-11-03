"""Run the discovery-planning agent and construct source-targeted queries."""

from app.agents.discovery_agent import DiscoveryAgent
from app.agents.registry import get_agent_profile
from app.services.agent_runtime import create_agent_task, run_agent_task
from app.services.source_adapters import build_source_queries


MAX_SEARCH_QUERIES = 15


def plan_discovery(user_request, workflow_id, parent_task_id=None):
    profile = get_agent_profile("discovery_planner")
    task = create_agent_task(
        "discovery_planner",
        workflow_id,
        {"user_request": user_request},
        parent_task_id=parent_task_id,
        privacy_classification="user_provided",
    )
    result = run_agent_task(
        task,
        lambda payload: DiscoveryAgent().execute(
            payload["user_request"],
            timeout_seconds=profile.timeout_seconds,
            max_output_tokens=profile.max_output_tokens,
            allowed_providers=profile.allowed_providers,
        ),
    )
    if result.status != "succeeded":
        raise RuntimeError("Discovery planning agent did not return a valid plan.")

    plan = result.structured_output
    intent = " ".join((user_request, *plan.get("keywords", [])[:5]))
    source_queries = build_source_queries(intent)
    queries = (
        plan.get("search_queries", [])[:5]
        + [item["query"] for item in source_queries]
    )[:MAX_SEARCH_QUERIES]
    if not queries:
        raise ValueError("Discovery plan did not produce any search queries")
    return plan, source_queries, queries, result.model_dump(mode="json")
