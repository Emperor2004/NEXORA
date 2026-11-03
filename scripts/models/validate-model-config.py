"""Validate model metadata and routing against the backend example settings."""

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def load_yaml(relative):
    with (ROOT / relative).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def env_example_values():
    text = (ROOT / "backend" / ".env.example").read_text(encoding="utf-8")
    return dict(re.findall(r"^([A-Z0-9_]+)=(.*)$", text, flags=re.MULTILINE))


def main():
    model_registry = load_yaml(Path("models/registry/model-registry.yaml"))
    providers = load_yaml(Path("models/registry/provider-registry.yaml")).get("providers", {})
    routes = load_yaml(Path("models/registry/agent-model-routing.yaml")).get("routing", {})
    env = env_example_values()

    assert model_registry.get("schema_version") == 1
    assert {entry.get("provider") for entry in model_registry["models"].values()} <= set(providers)
    assert model_registry["models"]["local_default"]["default_model"] == env["OLLAMA_MODEL"]
    assert model_registry["models"]["cloud_fallback"]["default_model"] == env["GEMINI_MODEL"]
    for name, route in routes.items():
        assert route["timeout_seconds"] > 0, f"{name}: timeout must be positive"
        assert route["allowed_providers"] is not None
        assert set(route["allowed_providers"]) <= set(providers), name
        limit = route.get("max_output_tokens")
        assert limit is None or limit > 0, name
    assert {"discovery_planner", "opportunity_extractor", "workflow_supervisor"} <= set(routes)
    print(f"PASS: {len(model_registry['models'])} model profiles, {len(providers)} providers, {len(routes)} agent routes")


if __name__ == "__main__":
    main()
