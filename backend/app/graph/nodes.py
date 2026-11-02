from app.agents.discovery_agent import DiscoveryAgent

discovery_agent = DiscoveryAgent()


def discovery_node(state):

    try:
        result = discovery_agent.execute(
            state["user_request"]
        )

        return {
            "plan": result,
            "error": ""
        }

    except Exception as error:
        return {
            "error": str(error)
        }
