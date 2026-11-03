# NEXORA

NEXORA is a local-first internship discovery and application research tool.
It searches public sources, retrieves vacancy pages, extracts details with
source evidence, assesses eligibility, ranks results, and tracks applications
that a user chooses to manage.

> **Status: prototype.** Discovery, evidence validation, initial employer
> verification signals, eligibility/ranking, local persistence, and a React
> interface are implemented. Search coverage, vacancy accuracy, security, and
> production reliability are not established.

## Core principles

- **Evidence before inference.** Missing or unsupported facts remain unknown.
- **Source provenance.** Preserve original posting links and the adapters that
  discovered them.
- **Independent verification.** An official or job-board domain alone does not
  prove an employer or vacancy is authentic.
- **User control.** NEXORA tracks applications but never submits them.
- **Respect access rules.** Discovery uses public search and bounded page
  retrieval; it does not bypass login, access controls, or anti-bot systems.

## Current capabilities

- Source-targeted discovery for government portals, research institutions,
  universities, company career pages, Internshala, Indeed, Naukri, Foundit,
  Wellfound, and LinkedIn.
- Within-run cross-source deduplication with additional source links retained.
- Bounded HTML/PDF retrieval, structured extraction, and evidence checks.
- Conservative eligibility assessment and explainable ranking.
- Evidence-quoted fraud-risk review cues and separate employer verification
  status. Risk cues are not authenticity verdicts.
- SQLite persistence and manual application status history.
- React/TypeScript pages for discovery, opportunity/source review, and
  application tracking.

The search and extraction coverage is not exhaustive. Platform layouts and
public availability vary. Most listings are not independently corroborated;
review the original announcement before applying.

## Architecture

```text
frontend/src/
  lib/                 API client
  ui/components/       Shared opportunity components and query hooks
  ui/pages/            Dashboard, discovery, opportunity, application, settings

backend/app/
  agents/              Agent implementations and registry
  api/                 API package boundary
  graph/               LangGraph state and orchestration
  schemas/             API and agent contracts
  services/            Search, retrieval, extraction, verification, storage
    workflow_planner.py
    workflow_source_resolver.py
    workflow_document_processor.py
    workflow_matching.py
    workflow_result_builder.py
    internship_workflow_service.py  Stable workflow facade

models/                Provider/agent registry, prompts, evaluation fixtures
scripts/               Setup, local development, model and quality commands
backend/tests/fixtures/ Small versioned regression datasets
data/discovery_runs/   Local generated discovery output (ignored by Git)
```

See [docs/modular-architecture.md](docs/modular-architecture.md) for module
responsibilities and change rules. The design proposals and implementation
records are in [NEXORA_AGENTIC_AI_ARCHITECTURE.md](NEXORA_AGENTIC_AI_ARCHITECTURE.md),
[NEXORA_README_MultiSource.md](NEXORA_README_MultiSource.md),
[NEXORA_ROOT_FOLDERS_STRUCTURE.md](NEXORA_ROOT_FOLDERS_STRUCTURE.md), and
the [implementation plan](docs/root-folders-implementation-plan.md).

## Quick start on Windows

From the repository root in PowerShell:

```powershell
.\scripts\setup\setup-backend.ps1
.\scripts\setup\setup-frontend.ps1
Copy-Item backend\.env.example backend\.env
.\scripts\dev\start-nexora.ps1
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173) for the interface or
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the API docs.
Stop the two recorded server windows with:

```powershell
.\scripts\dev\stop-nexora.ps1
```

The default local model provider is Ollama with `qwen2.5:3b`. Install/start
Ollama and pull that model if local inference is needed. Gemini is an optional
configured fallback. When used, relevant prompt content is sent to the
configured external provider. Review privacy implications before supplying
candidate details.

The frontend API URL defaults to `http://127.0.0.1:8000`. Set
`VITE_API_BASE_URL` in `frontend/.env.local` to change it. Never put a bearer
token in a `VITE_` variable: Vite embeds those values in browser assets. Enter
an optional `NEXORA_API_TOKEN` in the Settings page; the client keeps it in
memory for the current tab only.

## Configuration

Copy `backend/.env.example` to `backend/.env` and configure only the values you
need:

| Variable | Purpose |
| --- | --- |
| `OLLAMA_MODEL` | Local model name; defaults to `qwen2.5:3b`. |
| `LLM_PRIMARY_PROVIDER` | Primary provider; defaults to Ollama. |
| `LLM_FALLBACK_PROVIDER` | Optional fallback; defaults to Gemini. |
| `GEMINI_API_KEY` | Optional Gemini credential. Keep it out of source control. |
| `GEMINI_MODEL` | Gemini model name used when the fallback is enabled. |
| `NEXORA_API_TOKEN` | Optional bearer-token protection for API routes. Without it, API access is limited to loopback clients. |
| `NEXORA_CORS_ORIGINS` | Comma-separated allowed frontend origins; defaults to local Vite origins. |
| `NEXORA_DB_PATH` | Optional SQLite database path. Defaults to `backend/data/nexora.sqlite3`. |

The local API is not intended to be exposed directly to the public internet.
Remote access needs a deliberate authentication and trusted TLS deployment
design.

## API overview

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/health` | API health check. |
| `GET` | `/health/ollama` | Local model connection check. |
| `POST` | `/api/discovery/plan` | Produce a structured discovery plan. |
| `POST` | `/api/workflow/run` | Run bounded discovery through ranking and persistence. |
| `GET` | `/api/opportunities` | List persisted opportunities. |
| `GET` | `/api/opportunities/{id}` | Get an opportunity with source and evidence data. |
| `GET` | `/api/opportunities/{id}/application-checklist` | Return source-stated application details and user checks. |
| `GET` | `/api/applications` | List tracked applications. |
| `POST` | `/api/applications` | Start tracking an opportunity. |
| `PATCH` | `/api/applications/{id}` | Update an application status. |

See `/docs` for exact request and response schemas. Workflow runs are
synchronous and bounded to 1–10 requested results.

## Tests and checks

Run the focused offline validation suite from the repository root:

```powershell
.\scripts\quality\run-all-tests.ps1
```

It checks model metadata, synthetic fixture consistency, focused backend
regressions, the frontend production build, and frontend unit tests. It does
not run live-source accuracy, load, or full browser/API end-to-end tests.
Individual commands and their scope are documented in
[scripts/README.md](scripts/README.md).

## Data and Git hygiene

- Keep `.env`, API keys, bearer tokens, local databases, model weights, and
  generated discovery output out of Git.
- Small, reviewed regression inputs belong in `backend/tests/fixtures/`.
- Runtime discovery results are written under `data/discovery_runs/` and are
  ignored. They can contain large or changing source content.
- Do not store private candidate profiles or application information in test
  fixtures.

The repository has no verified license. Do not assume redistribution rights
until a license is added.
