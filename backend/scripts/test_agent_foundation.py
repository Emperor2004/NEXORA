"""Offline checks for typed agent profiles, envelopes, and LangGraph wiring."""

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.registry import AGENT_PROFILES, get_agent_profile, list_agent_profiles
from app.graph.workflow import (
    build_supervisor_graph,
    run_discovery_workflow,
    run_supervised_workflow,
)
from langgraph.checkpoint.memory import MemorySaver
from app.schemas.agent import AgentTaskEnvelope
from app.services.agent_runtime import create_agent_task, run_agent_task
from app.services import llm_service
from app.services.model_trace import record_model_call


def valid_plan():
    return {
        "search_queries": ["AI research internship India"],
        "target_domains": ["Artificial Intelligence"],
        "hard_constraints": [],
        "preferences": [],
        "keywords": ["AI", "research"],
        "exclusions": [],
        "reasoning": "Target AI research internships.",
    }


def test_registry_and_typed_task_result():
    profiles = {profile.name: profile for profile in list_agent_profiles()}
    assert set(profiles) == {
        "workflow_supervisor", "discovery_planner", "opportunity_extractor"
    }
    assert all(profile.lifecycle == "integrated" for profile in profiles.values())
    task = create_agent_task(
        "discovery_planner", "wf-test", {"user_request": "Find AI research internships"},
        privacy_classification="user_provided",
    )
    assert task.deadline > datetime.now(timezone.utc)
    assert "input_payload" not in task.model_dump()
    result = run_agent_task(task, lambda payload: valid_plan())
    assert result.status == "succeeded"
    assert result.structured_output["search_queries"] == ["AI research internship India"]
    assert result.token_and_cost_metadata["usage"] == "unavailable"

    traced = run_agent_task(task, lambda payload: (
        record_model_call("ollama", "qwen2.5:3b") or valid_plan()
    ))
    assert traced.model_provider == "ollama"
    assert traced.model_name == "qwen2.5:3b"


def test_retry_budget_and_provider_policy():
    original = AGENT_PROFILES["discovery_planner"]
    AGENT_PROFILES["discovery_planner"] = original.model_copy(update={"max_retries": 1})
    calls = []

    def flaky(payload):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("temporary failure")
        return valid_plan()

    try:
        task = create_agent_task(
            "discovery_planner", "wf-retry", {"user_request": "Find AI research internships"}
        )
        result = run_agent_task(task, flaky)
        assert result.status == "succeeded"
        assert len(calls) == 2
        assert result.tool_trace[0]["attempts"] == 2
    finally:
        AGENT_PROFILES["discovery_planner"] = original

    AGENT_PROFILES["discovery_planner"] = original.model_copy(update={"timeout_seconds": 1})
    try:
        timed_task = create_agent_task(
            "discovery_planner", "wf-timeout", {"user_request": "Find AI research internships"}
        )
        timed_result = run_agent_task(
            timed_task,
            lambda payload: (time.sleep(1.05) or valid_plan()),
        )
        assert timed_result.status == "retryable_failure"
        assert not timed_result.structured_output
    finally:
        AGENT_PROFILES["discovery_planner"] = original

    provider_calls = []

    def mock_provider(*args, **kwargs):
        provider_calls.append(kwargs)
        return {"ok": True}

    with (
        patch.object(llm_service, "PRIMARY_PROVIDER", "local_test"),
        patch.object(llm_service, "FALLBACK_PROVIDER", "cloud_test"),
        patch.dict(llm_service.PROVIDERS, {
            "local_test": mock_provider, "cloud_test": mock_provider,
        }),
    ):
        llm_service.generate_structured_output(
            "system", "user", {}, timeout_seconds=7,
            max_output_tokens=33, allowed_providers=("local_test", "cloud_test"),
        )
        try:
            llm_service.generate_structured_output(
                "system", "user", {}, provider="cloud_test",
                allowed_providers=("local_test",),
            )
        except ValueError as error:
            assert "not allowed" in str(error)
        else:
            raise AssertionError("Disallowed provider selection was accepted")
    assert provider_calls == [{"timeout_seconds": 7, "max_output_tokens": 33}]


def test_invalid_inputs_and_expired_deadlines_fail_closed():
    task = create_agent_task("discovery_planner", "wf-test", {"user_request": "short"})
    result = run_agent_task(task, lambda payload: valid_plan())
    assert result.status == "terminal_failure"
    assert "schema validation" in result.warnings[0]

    expired = task.model_copy(update={
        "input_payload": {"user_request": "Find AI research internships"},
        "deadline": datetime.now(timezone.utc) - timedelta(seconds=1),
    })
    expired_result = run_agent_task(expired, lambda payload: valid_plan())
    assert expired_result.status == "retryable_failure"

    try:
        AgentTaskEnvelope(
            workflow_id="wf", task_id="task", agent_name="discovery_planner",
            agent_version="1.0.0", deadline=datetime.now(),
            requested_output_schema="DiscoveryPlan",
        )
    except ValueError as error:
        assert "timezone" in str(error)
    else:
        raise AssertionError("Naive task deadlines were accepted")


def test_discovery_graph_uses_registered_agent_contract():
    with patch("app.graph.nodes.discovery_agent.execute", return_value=valid_plan()):
        result = run_discovery_workflow("Find AI research internships")
    assert result["workflow_status"] == "succeeded"
    assert result["plan"]["target_domains"] == ["Artificial Intelligence"]
    assert result["agent_runs"][0]["agent_name"] == "discovery_planner"


def test_supervisor_graph_preserves_workflow_response_shape():
    def fake_runner(**kwargs):
        assert kwargs["candidate_profile"]["degrees"] == ["B.Tech"]
        return {
            "summary": {"failures": 0, "individual_opportunities_extracted": 0},
            "opportunities": [],
            "errors": [],
            "agent_runs": [],
        }

    result = run_supervised_workflow(
        "Find AI research internships",
        candidate_profile={"degrees": ["B.Tech"]},
        max_results=2,
        workflow_runner=fake_runner,
    )
    assert result["workflow_status"] == "succeeded"
    assert result["summary"]["failures"] == 0
    assert result["agent_runs"][0]["agent_name"] == "workflow_supervisor"

    checkpointer = MemorySaver()
    graph = build_supervisor_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "wf-checkpoint-test", "workflow_runner": fake_runner}}
    state = graph.invoke({
        "workflow_id": "wf-checkpoint-test",
        "user_request": "Find AI research internships",
        "candidate_profile": {"degrees": ["B.Tech"]},
        "max_results": 2,
        "workflow_status": "pending",
    }, config=config)
    checkpoint = graph.get_state(config)
    assert checkpoint.values["workflow_id"] == state["workflow_id"]
    assert checkpoint.values["workflow_status"] == "succeeded"


def main():
    test_registry_and_typed_task_result()
    print("PASS: registered profiles execute through typed task/result envelopes")
    test_invalid_inputs_and_expired_deadlines_fail_closed()
    print("PASS: invalid inputs and expired tasks fail closed")
    test_discovery_graph_uses_registered_agent_contract()
    print("PASS: discovery planning graph records a versioned agent run")
    test_supervisor_graph_preserves_workflow_response_shape()
    print("PASS: LangGraph supervisor preserves API fields and creates run-scoped checkpoints")
    test_retry_budget_and_provider_policy()
    print("PASS: retry limits, provider allowlists, token caps, and timeouts are enforced")


if __name__ == "__main__":
    main()
