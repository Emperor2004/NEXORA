from datetime import datetime, timezone
import logging
from uuid import uuid4

from app.agents.discovery_agent import DiscoveryAgent
from app.agents.registry import get_agent_profile
from app.services.agent_runtime import create_agent_task, run_agent_task


logger = logging.getLogger("nexora.graph")
discovery_agent = DiscoveryAgent()


def discovery_node(state):
    workflow_id = state.get("workflow_id") or str(uuid4())
    profile = get_agent_profile("discovery_planner")
    task = create_agent_task(
        "discovery_planner",
        workflow_id,
        {"user_request": state["user_request"]},
        privacy_classification="user_provided",
    )
    result = run_agent_task(
        task,
        lambda payload: discovery_agent.execute(
            payload["user_request"],
            timeout_seconds=profile.timeout_seconds,
            max_output_tokens=profile.max_output_tokens,
            allowed_providers=profile.allowed_providers,
        ),
    )
    if result.status != "succeeded":
        logger.warning("Discovery planning did not complete: workflow_id=%s", workflow_id)
        return {
            "workflow_id": workflow_id,
            "error": "; ".join(result.warnings) or result.status,
            "workflow_status": result.status,
            "agent_runs": [result.model_dump(mode="json")],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "workflow_id": workflow_id,
        "plan": result.structured_output,
        "discovery_plan": result.structured_output,
        "error": "",
        "workflow_status": "succeeded",
        "agent_runs": [result.model_dump(mode="json")],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def supervisor_node(state, config=None):
    from app.services.internship_workflow_service import InternshipWorkflow

    workflow_id = state.get("workflow_id") or str(uuid4())
    profile = get_agent_profile("workflow_supervisor")
    payload = {
        "user_request": state["user_request"],
        "candidate_profile": state.get("candidate_profile"),
        "max_results": state.get("max_results", 5),
    }
    task = create_agent_task(
        "workflow_supervisor",
        workflow_id,
        payload,
        privacy_classification=(
            "candidate_profile" if payload["candidate_profile"] else "user_provided"
        ),
    )
    runner = (config or {}).get("configurable", {}).get("workflow_runner")
    if runner is None:
        runner = InternshipWorkflow().run
    result = run_agent_task(
        task,
        lambda task_input: runner(
            user_request=task_input["user_request"],
            candidate_profile=task_input["candidate_profile"],
            max_results=task_input["max_results"],
            workflow_id=workflow_id,
            parent_task_id=task.task_id,
        ),
    )
    if result.status != "succeeded":
        return {
            "workflow_id": workflow_id,
            "workflow_status": result.status,
            "workflow_result": {},
            "errors": [{"stage": "supervisor", "message": warning}
                       for warning in result.warnings],
            "agent_runs": [result.model_dump(mode="json")],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    workflow_result = result.structured_output
    summary = workflow_result.get("summary", {})
    workflow_status = "partial" if summary.get("failures", 0) else "succeeded"
    audit_result = result.model_copy(update={
        "status": workflow_status,
        "structured_output": {"summary": summary},
    })
    agent_runs = workflow_result.get("agent_runs", [])
    agent_runs.insert(0, audit_result.model_dump(mode="json"))
    errors = workflow_result.get("errors", [])
    review_queue = list(workflow_result.get("url_match_review", []))
    review_queue.extend(
        {
            "opportunity_id": item.get("opportunity_id"),
            "source_url": item.get("source", {}).get("url"),
            "record_status": item.get("record_status"),
            "eligibility_status": item.get("eligibility", {}).get("status"),
            "fraud_risk": item.get("verification", {}).get("fraud_risk", {}).get("level"),
        }
        for item in workflow_result.get("opportunities", [])
        if (
            item.get("record_status") == "needs_human_review"
            or item.get("eligibility", {}).get("status") == "needs_review"
            or item.get("verification", {}).get("fraud_risk", {}).get("level") == "elevated_review"
        )
    )
    return {
        "workflow_id": workflow_id,
        "workflow_status": workflow_status,
        "workflow_result": workflow_result,
        "discovery_plan": workflow_result.get("plan"),
        "discovery_candidates": workflow_result.get("discovery_candidates", []),
        "resolved_opportunities": workflow_result.get("opportunities", []),
        "retrieved_documents": workflow_result.get("retrieved_documents", []),
        "extracted_opportunities": workflow_result.get("opportunities", []),
        "verification_reports": [item.get("verification", {})
                                 for item in workflow_result.get("opportunities", [])],
        "eligibility_assessments": [item.get("eligibility", {})
                                    for item in workflow_result.get("opportunities", [])],
        "rankings": [item.get("ranking", {})
                     for item in workflow_result.get("opportunities", [])],
        "errors": errors,
        "review_queue": review_queue,
        "agent_runs": agent_runs,
        "created_at": state.get("created_at") or datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
