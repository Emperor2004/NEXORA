"""Bounded task execution and audit envelopes for registered agents."""

from datetime import datetime, timedelta, timezone
import logging
import time
from typing import Any, Callable
from uuid import uuid4

from app.agents.registry import get_agent_profile
from app.schemas.agent import (
    AgentResultEnvelope,
    AgentTaskEnvelope,
    DiscoveryPlannerInput,
    OpportunityExtractorInput,
    WorkflowSupervisorInput,
)
from app.services.model_trace import (
    get_model_trace,
    reset_model_trace,
    start_model_trace,
)


logger = logging.getLogger("nexora.agent_runtime")

INPUT_CONTRACTS = {
    "DiscoveryPlanRequest": DiscoveryPlannerInput,
    "RetrievedDocument": OpportunityExtractorInput,
    "WorkflowRunRequest": WorkflowSupervisorInput,
}


def create_agent_task(
    agent_name: str,
    workflow_id: str,
    input_payload: dict[str, Any],
    *,
    parent_task_id: str | None = None,
    input_reference_ids: list[str] | None = None,
    privacy_classification: str | None = None,
) -> AgentTaskEnvelope:
    profile = get_agent_profile(agent_name)
    now = datetime.now(timezone.utc)
    return AgentTaskEnvelope(
        workflow_id=workflow_id,
        task_id=str(uuid4()),
        parent_task_id=parent_task_id,
        agent_name=profile.name,
        agent_version=profile.version,
        input_reference_ids=input_reference_ids or [],
        deadline=now + timedelta(seconds=profile.timeout_seconds),
        privacy_classification=(privacy_classification or profile.privacy_classification),
        requested_output_schema=profile.output_schema,
        input_payload=input_payload,
    )


def run_agent_task(
    task: AgentTaskEnvelope,
    handler: Callable[[dict[str, Any]], dict[str, Any]],
) -> AgentResultEnvelope:
    """Run a synchronous handler under its profile's deadline/retry budget.

    External model and network clients must also receive bounded timeouts; the
    post-call deadline check prevents a late result from being labeled success.
    """
    profile = get_agent_profile(task.agent_name)
    if task.agent_version != profile.version:
        raise ValueError("Task agent version does not match the registered profile")
    if profile.lifecycle != "integrated":
        raise ValueError(f"Agent '{profile.name}' is not enabled")
    contract = INPUT_CONTRACTS.get(profile.input_schema)
    if contract is None:
        raise ValueError(f"No input contract is registered for '{profile.input_schema}'")
    started = datetime.now(timezone.utc)
    started_clock = time.monotonic()
    profile_deadline = started + timedelta(seconds=profile.timeout_seconds)
    effective_deadline = min(task.deadline, profile_deadline)
    model_trace_token = start_model_trace()
    warnings = []
    output = {}
    attempts = 0
    status = "terminal_failure"
    try:
        validated_input = contract.model_validate(task.input_payload).model_dump()
    except Exception as exc:
        validated_input = {}
        warnings.append(f"Agent input failed schema validation: {type(exc).__name__}.")
    if warnings:
        loop_range = range(0)
    else:
        remaining_retries = max(0, profile.max_retries - task.retry_count)
        loop_range = range(remaining_retries + 1)
    for _ in loop_range:
        if datetime.now(timezone.utc) >= effective_deadline:
            status = "retryable_failure"
            warnings.append("Task deadline elapsed before execution completed.")
            break
        attempts += 1
        try:
            output = handler(validated_input)
            if not isinstance(output, dict):
                raise TypeError("Agent handler must return a structured dictionary")
            if profile.output_schema == "DiscoveryPlan":
                from app.agents.discovery_agent import DiscoveryPlan
                output = DiscoveryPlan.model_validate(output).model_dump()
            elif profile.output_schema == "OpportunityExtraction":
                from app.schemas.opportunity import OpportunityExtraction
                if "extraction" not in output:
                    raise ValueError("Extraction result is missing its typed extraction payload")
                output["extraction"] = OpportunityExtraction.model_validate(
                    output["extraction"]
                ).model_dump()
            elif profile.output_schema == "WorkflowRunResult":
                if not isinstance(output.get("summary"), dict) or not isinstance(
                    output.get("opportunities"), list
                ):
                    raise ValueError("Workflow result does not match its output contract")
            if datetime.now(timezone.utc) > effective_deadline:
                status = "retryable_failure"
                warnings.append("Task exceeded its execution deadline; late result discarded.")
            else:
                status = "succeeded"
            break
        except Exception as exc:
            logger.warning(
                "Agent task failed: agent=%s workflow_id=%s task_id=%s attempt=%d error_type=%s",
                profile.name, task.workflow_id, task.task_id, attempts, type(exc).__name__,
            )
            if attempts <= remaining_retries and datetime.now(timezone.utc) < effective_deadline:
                time.sleep(min(0.25 * (2 ** (attempts - 1)), 1.0))
                continue
            status = "terminal_failure"
            warnings.append(f"Agent task failed with {type(exc).__name__}.")
            break

    elapsed = time.monotonic() - started_clock
    model_trace = get_model_trace()
    result = AgentResultEnvelope(
        workflow_id=task.workflow_id,
        task_id=task.task_id,
        agent_name=profile.name,
        agent_version=profile.version,
        status=status,
        structured_output=output if status == "succeeded" else {},
        evidence_reference_ids=task.input_reference_ids,
        warnings=warnings,
        confidence_or_uncertainty="Provider token and cost usage is unavailable in the current adapter.",
        tool_trace=[{
            "operation": "registered_handler_invocation",
            "agent": profile.name,
            "attempts": attempts,
            "declared_tools": list(profile.tool_permissions),
        }],
        model_provider=model_trace.get("provider"),
        model_name=model_trace.get("model"),
        token_and_cost_metadata={
            "elapsed_seconds": round(elapsed, 3),
            "time_budget_seconds": profile.timeout_seconds,
            "output_token_budget": profile.max_output_tokens,
            "usage": "unavailable",
            "prompt_hash": model_trace.get("prompt_hash"),
        },
        started_at=started,
        completed_at=datetime.now(timezone.utc),
    )
    logger.info(
        "Agent task completed: agent=%s workflow_id=%s task_id=%s status=%s elapsed_seconds=%.3f",
        profile.name, task.workflow_id, task.task_id, result.status, elapsed,
    )
    reset_model_trace(model_trace_token)
    return result
