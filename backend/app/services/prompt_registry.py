"""Load versioned system prompts from the repository's models directory."""

import hashlib
from pathlib import Path
import re


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PROMPT_DIRECTORY = REPOSITORY_ROOT / "models" / "prompts" / "agents"
PROMPT_FILES = {
    "discovery_planner": "discovery_planner/system.md",
    "opportunity_extractor": "opportunity_extraction/system.md",
}


def load_agent_prompt(agent_name: str) -> dict[str, str]:
    relative_path = PROMPT_FILES.get(agent_name)
    if relative_path is None or not re.fullmatch(r"[a-z_]+", agent_name):
        raise ValueError(f"No prompt is registered for agent '{agent_name}'")
    path = PROMPT_DIRECTORY / relative_path
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Prompt file for '{agent_name}' is empty")
    return {
        "content": content,
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }
