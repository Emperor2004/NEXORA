"""Read non-secret agent model routing from the repository model registry."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ROUTING_FILE = REPOSITORY_ROOT / "models" / "registry" / "agent-model-routing.yaml"


@lru_cache(maxsize=1)
def _load_routing() -> dict[str, Any]:
    with ROUTING_FILE.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    routes = data.get("routing")
    if not isinstance(routes, dict):
        raise ValueError("Agent model routing file must contain a routing mapping")
    return routes


def get_model_route(agent_name: str) -> dict[str, Any]:
    routes = _load_routing()
    try:
        return dict(routes[agent_name])
    except KeyError as exc:
        raise ValueError(f"No model route configured for agent '{agent_name}'") from exc
