from langgraph.graph import StateGraph, START, END

from app.graph.state import DiscoveryState
from app.graph.nodes import discovery_node


def build_discovery_graph():

    workflow = StateGraph(DiscoveryState)

    workflow.add_node("discovery", discovery_node)

    workflow.add_edge(START, "discovery")

    workflow.add_edge("discovery", END)

    return workflow.compile()


discovery_graph = build_discovery_graph()


def run_discovery_workflow(user_request):

    return discovery_graph.invoke({
        "user_request": user_request
    })
