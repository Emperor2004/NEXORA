from getpass import getpass
from pathlib import Path

env_path = Path(__file__).resolve().parents[1] / ".env"

key = getpass("Enter your Gemini API key (input hidden): ").strip()

if not key:
    raise SystemExit("No API key entered. Configuration cancelled.")

updates = {
    "GEMINI_API_KEY": key,
    "GEMINI_MODEL": "gemini-2.5-flash",
    "LLM_PRIMARY_PROVIDER": "ollama",
    "LLM_FALLBACK_PROVIDER": "gemini",
    "OLLAMA_MODEL": "qwen2.5:3b",
}

lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
output = []
written = set()

for line in lines:
    stripped = line.strip()

    if stripped and not stripped.startswith("#") and "=" in line:
        name = line.split("=", 1)[0].strip()

        if name in updates:
            output.append(f"{name}={updates[name]}")
            written.add(name)
            continue

    output.append(line)

for name, value in updates.items():
    if name not in written:
        output.append(f"{name}={value}")

env_path.write_text("\n".join(output) + "\n", encoding="utf-8")

print(f"Configuration saved to: {env_path}")
print("API key value was not displayed.")
