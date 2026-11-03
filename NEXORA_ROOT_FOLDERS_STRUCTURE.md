# NEXORA AI --- Root Folder Structure & Responsibilities

> **Purpose:** Define what belongs in the currently empty root-level
> `frontend/`, `models/`, and `scripts/` directories, including their
> recommended file structures, responsibilities, boundaries, and
> implementation order.
>
> **Architecture alignment:** This specification follows NEXORA's
> multi-source internship intelligence vision and the 12-agent target
> architecture. It describes the intended structure; it does not claim
> that these files or features already exist.

------------------------------------------------------------------------

## 1. Repository-level layout

Recommended target layout:

``` text
NEXORA/
│
├── backend/                         # Existing Python/FastAPI application
│   ├── app/
│   │   ├── agents/
│   │   ├── api/
│   │   ├── core/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── workflows/
│   ├── scripts/                      # Backend-only utilities and tests
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                        # React + TypeScript dashboard
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── lib/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── styles/
│   │   ├── types/
│   │   └── main.tsx
│   ├── tests/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── .env.example
│
├── models/                           # Model registry, prompts, evaluation and local artifacts
│   ├── registry/
│   ├── prompts/
│   │   ├── shared/
│   │   └── agents/
│   ├── configs/
│   ├── evaluations/
│   │   ├── datasets/
│   │   ├── results/
│   │   └── reports/
│   ├── adapters/
│   └── artifacts/                    # Downloaded model weights; normally gitignored
│
├── scripts/                          # Repository-level developer and operations scripts
│   ├── dev/
│   ├── setup/
│   ├── data/
│   ├── models/
│   ├── quality/
│   └── release/
│
├── data/                             # Runtime data; normally gitignored
│   ├── discovery_runs/
│   ├── exports/
│   ├── cache/
│   └── fixtures/
│
├── docs/                             # Project and architecture documentation
│   ├── architecture/
│   ├── development/
│   └── operations/
│
├── .gitignore
├── README.md
├── LICENSE                           # Add only after choosing a license
└── pyproject.toml                    # Optional root tooling configuration
```

This is a target layout, not an instruction to move or rename existing
modules blindly. Before creating directories, inspect the current
repository and map existing files to these responsibilities. Keep
existing backend modules working.

------------------------------------------------------------------------

# 2. `frontend/` --- User-facing NEXORA dashboard

## Purpose

The frontend is the control and visibility layer for NEXORA. It should
allow a user to configure a candidate profile, start and monitor
discovery runs, inspect opportunities and evidence, understand
eligibility and risk assessments, prepare application materials, and
track application progress.

**Recommended stack:** - React - TypeScript - Vite - Tailwind CSS -
React Router - TanStack Query for server state - React Hook Form + Zod
for forms and validation - Recharts for analytics where useful -
Vitest + React Testing Library for tests

Use a component library only if it improves consistency and
accessibility. Do not add dependencies without a concrete need.

## Recommended file structure

``` text
frontend/
├── public/
│   ├── favicon.svg
│   └── images/
│
├── src/
│   ├── app/
│   │   ├── App.tsx
│   │   ├── router.tsx
│   │   ├── providers.tsx
│   │   └── query-client.ts
│   │
│   ├── assets/
│   │   ├── icons/
│   │   └── illustrations/
│   │
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Select.tsx
│   │   │   ├── Dialog.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Tooltip.tsx
│   │   │   ├── Skeleton.tsx
│   │   │   └── EmptyState.tsx
│   │   ├── data-display/
│   │   │   ├── DataTable.tsx
│   │   │   ├── MetricCard.tsx
│   │   │   └── StatusBadge.tsx
│   │   └── feedback/
│   │       ├── ErrorState.tsx
│   │       ├── LoadingState.tsx
│   │       └── ToastProvider.tsx
│   │
│   ├── features/
│   │   ├── dashboard/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   └── pages/
│   │   │       └── DashboardPage.tsx
│   │   │
│   │   ├── candidate-profile/
│   │   │   ├── components/
│   │   │   ├── schemas/
│   │   │   ├── hooks/
│   │   │   └── pages/
│   │   │       └── CandidateProfilePage.tsx
│   │   │
│   │   ├── discovery/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   └── pages/
│   │   │       ├── DiscoveryPage.tsx
│   │   │       └── DiscoveryRunPage.tsx
│   │   │
│   │   ├── opportunities/
│   │   │   ├── components/
│   │   │   │   ├── OpportunityCard.tsx
│   │   │   │   ├── OpportunityFilters.tsx
│   │   │   │   ├── EvidencePanel.tsx
│   │   │   │   ├── EligibilityPanel.tsx
│   │   │   │   └── VerificationPanel.tsx
│   │   │   ├── hooks/
│   │   │   └── pages/
│   │   │       ├── OpportunityListPage.tsx
│   │   │       └── OpportunityDetailPage.tsx
│   │   │
│   │   ├── applications/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   └── pages/
│   │   │       ├── ApplicationsPage.tsx
│   │   │       └── ApplicationDetailPage.tsx
│   │   │
│   │   ├── settings/
│   │   │   └── pages/
│   │   │       └── SettingsPage.tsx
│   │   │
│   │   └── agent-runs/
│   │       ├── components/
│   │       └── pages/
│   │           └── AgentRunDetailsPage.tsx
│   │
│   ├── hooks/
│   │   ├── useDebounce.ts
│   │   └── useConfirm.ts
│   │
│   ├── layouts/
│   │   ├── AppLayout.tsx
│   │   ├── Sidebar.tsx
│   │   ├── Topbar.tsx
│   │   └── AuthLayout.tsx
│   │
│   ├── lib/
│   │   ├── api-client.ts
│   │   ├── env.ts
│   │   ├── formatters.ts
│   │   └── query-keys.ts
│   │
│   ├── routes/
│   │   └── route-config.ts
│   │
│   ├── services/
│   │   ├── candidate.service.ts
│   │   ├── discovery.service.ts
│   │   ├── opportunities.service.ts
│   │   ├── applications.service.ts
│   │   └── agent-runs.service.ts
│   │
│   ├── styles/
│   │   ├── globals.css
│   │   └── tokens.css
│   │
│   ├── types/
│   │   ├── api.ts
│   │   ├── candidate.ts
│   │   ├── opportunity.ts
│   │   ├── application.ts
│   │   └── agent.ts
│   │
│   ├── test/
│   │   └── setup.ts
│   │
│   └── main.tsx
│
├── tests/
│   └── e2e/
│       ├── dashboard.spec.ts
│       ├── discovery.spec.ts
│       └── opportunity-review.spec.ts
│
├── .env.example
├── .gitignore
├── index.html
├── package.json
├── package-lock.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts               # If required by selected Tailwind version
└── README.md
```

The structure may be simplified if the initial UI is small. Avoid
creating empty placeholder components for every planned feature.

## Frontend pages and responsibilities

  -----------------------------------------------------------------------
  Page                                What it should show or do
  ----------------------------------- -----------------------------------
  Dashboard                           Discovery summary, new
                                      opportunities, saved opportunities,
                                      upcoming deadlines, application
                                      status overview.

  Candidate Profile                   Education, skills, projects,
                                      experience, preferences,
                                      availability, and profile
                                      completeness.

  Discovery                           Search criteria, source categories,
                                      filters, run controls, and
                                      discovery progress.

  Discovery Run                       Run status, sources queried,
                                      candidate counts, agent activity,
                                      failures, and partial results.

  Opportunity List                    Search, sort, filter, compare,
                                      save, and inspect opportunities.

  Opportunity Detail                  Original source, extracted fields,
                                      evidence quotes, eligibility,
                                      ranking explanation, verification,
                                      and risk indicators.

  Applications                        User-managed application pipeline
                                      and status history.

  Application Detail                  Checklist, draft documents,
                                      deadlines, notes, and
                                      user-confirmed events.

  Agent Run Details                   Agent-by-agent status,
                                      inputs/outputs summary, tool trace,
                                      errors, and timing.

  Settings                            LLM provider configuration
                                      visibility, search preferences,
                                      privacy settings, and notification
                                      preferences.
  -----------------------------------------------------------------------

## Frontend design rules

-   Make evidence visible. Users should be able to open the original
    source and inspect the quote supporting an extracted field.
-   Distinguish `verified`, `unverified`, `needs_review`, and
    suspicious/risk-flagged states visually.
-   Never use a single green "verified" badge merely because a page was
    fetched.
-   Display unknown fields as "Not stated" or "Unknown", not as zero or
    a fabricated value.
-   Explain eligibility and ranking; do not show unexplained scores.
-   Provide loading, empty, partial-result, and error states.
-   Ensure responsive layout and keyboard accessibility.
-   Do not expose API keys or provider secrets in frontend code.
-   The frontend must not submit an application without an explicit user
    confirmation step.

## Frontend-to-backend boundary

The frontend should call the FastAPI backend through a single API
client. It should not: - Call Ollama or Gemini directly. - Scrape
websites directly from the browser. - Perform eligibility or fraud
scoring as the source of truth. - Store secrets in `VITE_*` variables. -
Treat frontend validation as a substitute for backend validation.

The backend owns business rules, evidence, verification, scoring,
persistence, and authorization.

------------------------------------------------------------------------

# 3. `models/` --- Model registry, prompts, configuration and evaluation

## Purpose

The root `models/` directory should organize model-related assets and
governance. It should not become a second backend source tree.

Keep model integration logic and runtime orchestration in
`backend/app/`. Keep model metadata, prompt templates, model-specific
configuration, evaluation datasets, and optional local artifacts in root
`models/`.

**Important:** Do not commit large model weights, private datasets, API
keys, or downloaded model caches. Ollama normally manages its own model
storage outside this project. The `models/artifacts/` directory is only
for explicitly managed artifacts that the project needs to reference.

## Recommended file structure

``` text
models/
├── registry/
│   ├── model-registry.yaml
│   ├── provider-registry.yaml
│   └── agent-model-routing.yaml
│
├── prompts/
│   ├── shared/
│   │   ├── evidence_policy.md
│   │   ├── structured_output_policy.md
│   │   └── untrusted_content_policy.md
│   │
│   └── agents/
│       ├── candidate_profile/
│       │   └── system.md
│       ├── discovery_planner/
│       │   └── system.md
│       ├── multi_source_discovery/
│       │   └── system.md
│       ├── source_resolution/
│       │   └── system.md
│       ├── document_retrieval/
│       │   └── system.md
│       ├── opportunity_extraction/
│       │   └── system.md
│       ├── verification_fraud/
│       │   └── system.md
│       ├── eligibility/
│       │   └── system.md
│       ├── ranking/
│       │   └── system.md
│       ├── application_preparation/
│       │   └── system.md
│       └── application_tracking/
│           └── system.md
│
├── configs/
│   ├── local/
│   │   └── ollama.yaml
│   ├── cloud/
│   │   └── gemini.yaml
│   ├── routing/
│   │   └── default.yaml
│   └── inference/
│       └── generation-defaults.yaml
│
├── evaluations/
│   ├── datasets/
│   │   ├── extraction/
│   │   ├── eligibility/
│   │   ├── verification/
│   │   └── ranking/
│   ├── cases/
│   │   ├── legitimate-vacancies.jsonl
│   │   ├── duplicate-vacancies.jsonl
│   │   ├── suspicious-vacancies.jsonl
│   │   └── conflicting-fields.jsonl
│   ├── results/
│   │   └── .gitkeep
│   ├── reports/
│   │   └── .gitkeep
│   └── evaluation-config.yaml
│
├── adapters/
│   ├── README.md
│   └── model-capabilities.yaml
│
├── artifacts/
│   └── .gitkeep
│
├── .gitignore
└── README.md
```

The Supervisor/Orchestrator agent may not need an LLM prompt at all. It
should use deterministic workflow logic wherever possible. Do not create
a prompt file just to make the folder symmetrical.

## 3.1 `registry/`

### `model-registry.yaml`

Records model identifiers and capabilities, not credentials.

Example:

``` yaml
models:
  local_extraction:
    provider: ollama
    model: qwen2.5:3b
    enabled: true
    tasks:
      - structured_extraction
      - classification
    data_policy: local_only

  cloud_fallback:
    provider: gemini
    model: ${GEMINI_MODEL}
    enabled: false
    tasks:
      - complex_extraction_fallback
    data_policy: requires_cloud_permission
```

The model name and provider must match the actual installed/configured
integration. Do not assume a model exists because it appears in this
example.

### `provider-registry.yaml`

Defines provider capabilities, supported structured-output modes, health
checks, timeout defaults, and whether a provider sends prompts
externally.

### `agent-model-routing.yaml`

Maps agent/task types to model profiles. The mapping should be
configurable rather than hardcoded in each agent.

## 3.2 `prompts/`

Store version-controlled, role-specific system instructions here if the
backend loads prompts from files.

Each prompt should specify: - Agent identity and mission. - Input
context and allowed fields. - Output schema. - Evidence and uncertainty
policy. - Tool-use boundaries. - Failure and escalation behavior. -
Examples of valid and invalid outputs.

Prompts must not contain API keys, personal candidate data, or copied
vacancy-specific content.

Keep prompt versions traceable. A workflow run should record the prompt
version/hash used by each agent.

## 3.3 `configs/`

Configuration files should contain non-secret defaults such as model
parameters, provider selection policies, timeouts, and token budgets.

Secrets belong in environment variables or a proper secret manager,
never in YAML committed to Git.

## 3.4 `evaluations/`

This is essential for measuring whether the agents are actually
reliable.

Maintain labeled examples for: - Correct extraction of title,
organization, location, duration, stipend, and eligibility. - Unknown or
absent values that must remain null. - Conflicting statements across
page sections. - Duplicate postings across platforms. - Legitimate,
suspicious, and confirmed fraudulent examples. - Eligibility outcomes
with known ground truth. - Ranking examples reviewed by a human.

Do not store real candidate personal data in shared test fixtures. Use
synthetic or properly anonymized examples.

Evaluation reports should include dataset version, model/provider,
prompt version, metrics, error examples, and limitations.

## 3.5 `adapters/`

This directory is for model capability metadata or portable adapter
definitions. Actual Python provider implementations should remain in
`backend/app/services/` or the existing model service layer.

Do not store executable model code in two places.

------------------------------------------------------------------------

# 4. `scripts/` --- Repository-level automation

## Purpose

The root `scripts/` directory should contain developer, setup,
data-maintenance, model-management, quality, and release utilities that
operate across the repository.

It should not duplicate backend business logic or become a second
location for application services.

Use: - `backend/scripts/` for backend-specific diagnostics, data
processing, and backend tests. - Root `scripts/` for cross-project
commands such as starting both frontend and backend, checking the
repository, validating configuration, and preparing releases.

## Recommended file structure

``` text
scripts/
├── dev/
│   ├── start-backend.ps1
│   ├── start-frontend.ps1
│   ├── start-nexora.ps1
│   └── stop-nexora.ps1
│
├── setup/
│   ├── setup-backend.ps1
│   ├── setup-frontend.ps1
│   ├── check-prerequisites.ps1
│   └── verify-environment.ps1
│
├── data/
│   ├── validate-discovery-data.py
│   ├── inspect-opportunity-records.py
│   ├── export-opportunities.py
│   └── deduplicate-discovery-runs.py
│
├── models/
│   ├── check-ollama.ps1
│   ├── list-local-models.ps1
│   ├── validate-model-config.py
│   └── run-model-evaluation.py
│
├── quality/
│   ├── run-backend-tests.ps1
│   ├── run-frontend-tests.ps1
│   ├── run-all-tests.ps1
│   ├── run-lint.ps1
│   └── check-secrets.ps1
│
├── release/
│   ├── build-frontend.ps1
│   ├── pre-release-check.ps1
│   └── generate-version-info.py
│
└── README.md
```

Use PowerShell scripts for Windows-first developer workflows. Use Python
for data validation and cross-platform logic. If cross-platform support
becomes a requirement, add equivalent shell scripts or move shared logic
into Python.

## Script responsibilities

  -----------------------------------------------------------------------
  Folder                              Responsibility
  ----------------------------------- -----------------------------------
  `dev/`                              Start and stop the local
                                      application components.

  `setup/`                            Check prerequisites and set up
                                      development environments.

  `data/`                             Inspect, validate, export, or
                                      maintain local discovery datasets.

  `models/`                           Check local model availability and
                                      run model evaluations.

  `quality/`                          Run tests, linting, type checks,
                                      and secret scans.

  `release/`                          Build artifacts and run
                                      release-readiness checks.
  -----------------------------------------------------------------------

### Root script safety rules

-   Scripts must not delete databases, discovery data, model artifacts,
    or user files by default.
-   Destructive actions require an explicit flag and clear confirmation.
-   Do not hardcode absolute developer-specific paths such as
    `D:\Projects\NEXORA`.
-   Resolve the repository root relative to the script location.
-   Return non-zero exit codes when checks fail.
-   Print clear status and error messages.
-   Never print secrets or full environment files.
-   Keep scripts idempotent where possible.
-   Avoid duplicating functionality already available through package
    scripts or backend commands.

------------------------------------------------------------------------

# 5. Folder boundaries --- where code belongs

  -----------------------------------------------------------------------
  Concern                             Correct location
  ----------------------------------- -----------------------------------
  FastAPI routes and backend business `backend/app/`
  logic                               

  Agent Python implementations        `backend/app/agents/`

  LangGraph workflow definitions      `backend/app/workflows/`

  Pydantic schemas                    `backend/app/schemas/`

  Search, scraping adapters,          `backend/app/services/`
  retrieval, LLM provider code        

  Backend-only test/diagnostic        `backend/scripts/`
  scripts                             

  Backend automated tests             `backend/tests/`

  React pages and UI components       `frontend/src/`

  Frontend API client                 `frontend/src/lib/` and
                                      `frontend/src/services/`

  Model metadata and routing          `models/registry/`
  configuration                       

  Agent system prompts                `models/prompts/agents/`

  Model evaluation fixtures and       `models/evaluations/`
  reports                             

  Downloaded model files, if          `models/artifacts/` (gitignored by
  explicitly needed                   default)

  Cross-project developer commands    Root `scripts/`

  Runtime discovery data              Root `data/`

  Architecture and developer          `docs/`
  documentation                       
  -----------------------------------------------------------------------

Do not move existing code just to match this diagram. First map actual
modules and imports, then migrate only when there is a concrete benefit
and tests cover the change.

------------------------------------------------------------------------

# 6. Environment variables and secrets

### Frontend `.env.example`

Only non-secret public configuration should use Vite's `VITE_` prefix:

``` dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Never place API keys, Gemini credentials, database credentials, or
private tokens in frontend environment variables. Vite variables are
exposed to the browser bundle.

### Backend `.env`

Backend-only secrets and provider configuration remain in
`backend/.env`, for example:

``` dotenv
LLM_PRIMARY_PROVIDER=ollama
LLM_FALLBACK_PROVIDER=gemini
OLLAMA_MODEL=qwen2.5:3b

# Configure only if cloud fallback is enabled.
# GEMINI_MODEL=<configured-model>
# GEMINI_API_KEY=<secret>
# NEXORA_API_TOKEN=<strong-random-token>
```

The actual backend settings schema and `.env.example` are authoritative.

------------------------------------------------------------------------

# 7. Git ignore requirements

Ensure `.gitignore` excludes at least:

``` gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Secrets
.env
.env.*
!.env.example

# Frontend
frontend/node_modules/
frontend/dist/
frontend/.vite/
frontend/coverage/

# Runtime data
data/cache/
data/exports/
data/discovery_runs/
backend/data/*.sqlite3
*.db
*.sqlite3

# Model artifacts and caches
models/artifacts/*
!models/artifacts/.gitkeep
**/model_cache/
*.gguf
*.safetensors
*.pt
*.pth
*.onnx

# Logs and temporary files
*.log
logs/
tmp/
temp/

# OS/editor
.DS_Store
Thumbs.db
.vscode/
.idea/
```

Review the existing `.gitignore` before replacing it. Do not
accidentally ignore small, intentional, version-controlled evaluation
fixtures or sample data. Add only safe, anonymized fixtures to Git.

------------------------------------------------------------------------

# 8. Implementation order

Do not populate every folder with placeholder files at once. Implement
in a dependency-aware order.

## Phase 1 --- Repository audit and contracts

-   [ ] Inspect current root, backend, and data directories.
-   [ ] Record existing files and identify overlaps with this
    specification.
-   [ ] Confirm backend API routes and schemas that the frontend will
    consume.
-   [ ] Define frontend/backend API contracts.
-   [ ] Define model configuration and prompt-loading conventions.
-   [ ] Review `.gitignore` and secret handling.

**Acceptance:** A verified repository map and no duplicated or
conflicting ownership of modules.

## Phase 2 --- Root scripts foundation

-   [ ] Add prerequisite checks.
-   [ ] Add environment verification.
-   [ ] Add backend and frontend start scripts.
-   [ ] Add a combined local development launcher.
-   [ ] Add a quality script that runs existing backend tests.

**Acceptance:** A developer can validate the environment and start the
existing backend using repository-relative paths.

## Phase 3 --- Model registry and evaluation

-   [ ] Add model and provider registries based on actual working
    integrations.
-   [ ] Add model-routing configuration.
-   [ ] Move prompts into versioned files only if the backend can load
    them cleanly.
-   [ ] Add evaluation fixtures and a reproducible evaluation runner.
-   [ ] Record prompt/model versions in agent run metadata.

**Acceptance:** Model selection is configurable and measurable; no
credentials or large model weights are committed.

## Phase 4 --- Frontend foundation

-   [ ] Scaffold React + TypeScript + Vite.
-   [ ] Add the shared API client and typed API models.
-   [ ] Add app layout, routing, loading/error states, and design
    tokens.
-   [ ] Implement dashboard and opportunity list/detail pages against
    actual backend APIs.
-   [ ] Add candidate profile and application tracking pages when their
    APIs are ready.
-   [ ] Add component and end-to-end tests.

**Acceptance:** The frontend can consume the real backend API and
accurately display evidence, eligibility, verification, and application
states.

## Phase 5 --- Integration and hardening

-   [ ] Add a single local start workflow for frontend and backend.
-   [ ] Add end-to-end tests for discovery and opportunity review.
-   [ ] Add API error handling and session/token handling appropriate to
    the backend.
-   [ ] Check that no secrets are exposed in frontend builds.
-   [ ] Add build and release checks.

**Acceptance:** A user can start NEXORA locally, run discovery, inspect
evidence-backed opportunities, and manage application records without
bypassing backend controls.

------------------------------------------------------------------------

# 9. Instructions for Codex

Use this document as the target specification for the root-level
`frontend/`, `models/`, and `scripts/` directories.

**First task: audit, do not immediately scaffold.**

1.  Inspect the actual root repository tree and existing backend
    modules.
2.  Confirm which of these directories are empty and identify any
    existing files that overlap with this design.
3.  Inspect current FastAPI routes, Pydantic schemas, model provider
    service, agent prompt handling, and test commands.
4.  Produce a concise mapping of existing files to the target structure.
5.  Identify any changes required to the target structure based on the
    real code.
6.  Present a phased implementation plan and wait before making broad
    changes.

When implementation is authorized:

-   Preserve working backend behavior.
-   Do not duplicate backend scripts in the root scripts folder.
-   Do not invent frontend API routes; use the actual backend contracts.
-   Do not add placeholder agents, prompt files, or UI pages that have
    no implementation purpose.
-   Do not commit secrets, model weights, runtime databases, or private
    discovery data.
-   Add tests for meaningful functionality.
-   Update the relevant README files when a folder becomes operational.
-   Report created files, changed files, test results, and unfinished
    work.

**Definition of done:** Each folder has a clear responsibility,
meaningful implemented contents, documented setup, and tests appropriate
to its role. A directory containing only empty placeholders does not
count as completed.

------------------------------------------------------------------------

## 10. Final design principle

Keep the repository understandable:

-   `backend/` makes NEXORA work.
-   `frontend/` lets the user operate and understand NEXORA.
-   `models/` defines which models and prompts agents use and how their
    quality is evaluated.
-   `scripts/` makes development, testing, and operations repeatable.
-   `data/` holds runtime records and artifacts.
-   `docs/` explains the system and its operating procedures.

**Build a coherent product, not a large directory tree.**
