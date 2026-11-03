from datetime import datetime, timezone
from uuid import uuid4

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import DiscoveryState, NexoraWorkflowState
from app.graph.nodes import discovery_node, supervisor_node


def build_discovery_graph(checkpointer=None):
    workflow = StateGraph(DiscoveryState)
    workflow.add_node("discovery", discovery_node)
    workflow.add_edge(START, "discovery")
    workflow.add_edge("discovery", END)
    return workflow.compile(checkpointer=checkpointer)


def build_supervisor_graph(checkpointer=None):
    workflow = StateGraph(NexoraWorkflowState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_edge(START, "supervisor")
    workflow.add_edge("supervisor", END)
    return workflow.compile(checkpointer=checkpointer)


discovery_graph = build_discovery_graph()
supervisor_graph = build_supervisor_graph()


def run_discovery_workflow(user_request):
    now = datetime.now(timezone.utc).isoformat()
    workflow_id = str(uuid4())
    graph = build_discovery_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": workflow_id}}
    return graph.invoke({
        "workflow_id": workflow_id,
        "user_request": user_request,
        "workflow_status": "running",
        "agent_runs": [],
        "created_at": now,
        "updated_at": now,
    }, config=config)


def run_supervised_workflow(user_request, candidate_profile=None, max_results=5,
                            workflow_runner=None):
    now = datetime.now(timezone.utc).isoformat()
    invoke_state = {
        "workflow_id": str(uuid4()),
        "user_request": user_request,
        "candidate_profile": candidate_profile,
        "max_results": max_results,
        "workflow_status": "pending",
        "agent_runs": [],
        "errors": [],
        "created_at": now,
        "updated_at": now,
    }
    config = {"configurable": {
        "thread_id": invoke_state["workflow_id"],
        "workflow_runner": workflow_runner,
    }}
    graph = build_supervisor_graph(checkpointer=MemorySaver())
    state = graph.invoke(invoke_state, config=config)
    result = state.get("workflow_result", {})
    if not result and state.get("workflow_status") in {"retryable_failure", "terminal_failure"}:
        raise RuntimeError(
            "; ".join(item.get("message", "Workflow failed")
                       for item in state.get("errors", []))
            or "The supervised internship workflow failed."
        )
    return {
        **result,
        "workflow_id": state.get("workflow_id"),
        "workflow_status": state.get("workflow_status", "terminal_failure"),
        "agent_runs": state.get("agent_runs", []),
    }
