# Model configuration and evaluation data

The registry records NEXORA's actual backend defaults: Ollama with
`qwen2.5:3b` and an optional Gemini fallback. The backend remains the runtime
source of truth; these YAML files document compatible model profiles and are
validated by `scripts/models/validate-model-config.py`.

Prompts exist only for the two currently integrated LLM roles. Their files
are loaded by the backend using paths relative to the repository, and the
prompt SHA-256 is recorded in the agent run when a provider is called.

Evaluation cases are synthetic. `scripts/models/evaluate-fixtures.py` checks
fixture integrity only; it does not invoke models or report model accuracy.
Do not put candidate personal information, credentials, model weights, or
downloaded provider caches in this directory.
