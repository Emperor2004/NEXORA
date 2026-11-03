# Root folders audit and implementation plan

## Audit findings

- `frontend/`, `models/`, and root `scripts/` existed without implementation
  before this increment.
- The FastAPI backend already exposes health, discovery planning/workflow,
  opportunity, checklist, and application routes. The frontend must use those
  routes; there is no candidate-profile CRUD or agent-run history API.
- Backend provider defaults are Ollama `qwen2.5:3b` with Gemini fallback
  `gemini-3.8-flash`; Gemini configuration is optional and external.
- Agent prompts currently live in `discovery_agent.py` and
  `opportunity_extraction_agent.py`. Moving the two active prompts into
  versioned files is viable with a repository-relative loader and hash audit.
- Backend-only utilities/tests already live in `backend/scripts/`; root scripts
  will orchestrate repository tasks and will not duplicate those utilities.
- The current `.gitignore` protects secrets and the SQLite database but does
  not yet cover Python caches, frontend build outputs, runtime discovery data,
  or model artifacts.
- `backend/app/graph/` is already the working LangGraph package. It will stay
  in place; this increment will not rename it to match the target diagram.

## Implementation phases

### 1. Repository contracts and safety — implemented

Files: `.gitignore`, `backend/app/main.py`, `backend/.env.example`,
`frontend/.env.example`, `README.md`.

Add local Vite CORS origins, safe ignore patterns, and environment examples.
Acceptance: no secrets in the frontend example; Vite can reach the existing
loopback API; runtime output and model weights are ignored without ignoring
small evaluation fixtures.

### 2. Root developer scripts — implemented

Files: `scripts/dev/`, `scripts/setup/`, `scripts/quality/`,
`scripts/README.md`.

Add repository-relative prerequisite/environment checks and separate plus
combined local start/stop scripts. Quality scripts call a documented offline
backend suite and frontend checks. They must not delete databases or artifacts.

Acceptance: scripts resolve paths from their own location, fail with a
non-zero exit code when prerequisites/checks fail, and document loopback URLs.

### 3. Model registry, prompts, and fixture evaluation — implemented

Files: `models/registry/`, `models/configs/`, `models/prompts/agents/`,
`models/adapters/`, `models/evaluations/`,
`backend/app/services/prompt_registry.py`, and active agent modules.

Record the actual configured providers/models, external-data policy, timeouts,
and existing active agent routes. Move only the two active prompts into files,
load them relative to the repository, and attach prompt hashes to agent audit
metadata. Add synthetic evaluation cases and a fixture-integrity runner; it
must not claim model accuracy.

Acceptance: registry references agree with backend defaults, prompt loading is
covered offline, no credentials/weights/private records are added, and fixture
validation reports only integrity/coverage counts.

### 4. Frontend foundation — implemented

Files: `frontend/src/`, package/config files, frontend tests and README.

Build a small React/TypeScript app for dashboard, discovery run, opportunities,
and application tracking using current API schemas. Keep the API token in
memory only; allow a non-secret base URL through `VITE_API_BASE_URL`. Do not
add unsupported candidate/profile or agent-history screens.

Acceptance: frontend build and unit tests pass; API requests use one client,
loading/error/empty/partial states are visible, and evidence/source links and
verification status are shown without implying that a fetch proves legitimacy.

### 5. Integration and hardening — initial local integration implemented

Files: local launcher scripts, CORS policy, API client, release checks.

Combined startup and CORS policy are wired. Full end-to-end browser automation
can follow after the local API test-client issue is resolved.

Acceptance: local startup is configured for loopback addresses; no token is
embedded in the bundle; no application submission is triggered by the UI.

## Delivered implementation notes

- Frontend requests use existing backend routes and show loading, error, and
  empty states. The UI exposes evidence, original-source links, and
  verification/risk fields when returned by the backend.
- The optional bearer token is held only in JavaScript memory; the Vite
  environment example contains only the non-secret API base URL.
- The combined launcher opens both local servers in separate windows and
  records their process IDs and script paths. The stop script validates each
  recorded command line before terminating its process tree.
- The focused offline backend suite excludes networked checks and the Windows
  API TestClient scenario known to stall during startup.
- Responsive browser behavior and full API/browser integration remain
  unverified. Candidate profile persistence and the API gaps listed below
  remain outside this increment.

## Known boundary

The frontend can run discovery and manage opportunities/applications exposed by
the backend, but candidate-profile persistence, background run monitoring,
agent-run history, reminders, and application preparation are not exposed by
current routes and will remain unimplemented in this increment.
