# NEXORA AI

**A local-first, evidence-grounded AI platform for internship discovery,
eligibility assessment, recommendations, and application management.**

> **Status: Active development / prototype.** A bounded
> discovery-to-ranking API workflow and initial local application
> tracking are implemented. Production readiness, large-scale live
> discovery, eligibility accuracy across representative profiles, and
> deployment security are not yet verified.

## Overview

NEXORA is intended to act as a personal AI internship research and
application assistant. It discovers internship opportunities from public
sources, retrieves individual vacancy announcements, extracts structured
information, checks extracted claims against source evidence, assesses
candidate eligibility, ranks opportunities, and helps users manage
application progress.

NEXORA is not merely a job scraper or a chatbot over search results. Its
core principle is **evidence before inference**: missing information
remains unknown until supported by source material. A successful page
fetch does not prove that a vacancy is authentic, active, or suitable.

## Vision

The long-term workflow is:

**Discover → Retrieve → Extract → Validate → Assess → Rank → Prepare →
Track**

1.  Discover research and industry internships from public sources.
2.  Retrieve original vacancy announcements and supported documents.
3.  Extract structured vacancy information.
4.  Validate populated fields against source evidence.
5.  Assess candidate eligibility against stated requirements.
6.  Rank opportunities using explainable factors.
7.  Prepare application materials for user review.
8.  Track saved opportunities and application progress.

Target sources include government institutions, research laboratories,
universities, academic programmes, and private organizations. Coverage
depends on public accessibility, search indexing, website structure, and
access restrictions.

## Current implementation status

  ------------------------------------------------------------------------
  Capability             Status                 Notes
  ---------------------- ---------------------- --------------------------
  LLM provider           Implemented; fallback  Ollama primary, Gemini
  abstraction            tested                 fallback configured in
                                                development.

  Discovery planning     Implemented            Produces structured search
                                                plans and constraints.

  LangGraph              Partial                Discovery planning graph
                                                exists; full pipeline is a
                                                bounded Python service.

  Web discovery          Implemented; tested    Uses DDGS.

  Candidate parsing and  Implemented            Candidate integration,
  triage                                        deduplication, and
                                                three-tier triage have
                                                development tests.

  LinkedIn URL matching  Implemented            Finds and normalizes
                                                `/jobs/view/` links.

  HTML/PDF retrieval     Implemented            Includes URL checks,
                                                redirect limits, and
                                                download/text bounds.

  LinkedIn listing       Implemented            Parses candidate entries
  parser                                        from listing-page text.

  Deterministic LinkedIn Implemented;           Extracts title,
  metadata parser        regression-tested      organization, location,
                                                work mode, employment
                                                type, duration, stipend,
                                                and payment-related
                                                fields.

  LLM opportunity        Implemented            Uses a Pydantic schema and
  extraction                                    requests evidence
                                                quotations.

  Evidence validation    Implemented            Unsupported claims are
  and merge                                     removed or flagged;
                                                deterministic metadata is
                                                merged.

  Integrated workflow    Implemented; offline   `POST /api/workflow/run`
  API                    replay tested          performs bounded
                                                discovery,
                                                retrieval/extraction,
                                                assessment, ranking, and
                                                persistence. Live
                                                throughput is not
                                                established.

  Eligibility assessment Initial implementation Conservative rules;
                                                ambiguous or incomplete
                                                requirements may need
                                                human review.

  Explainable ranking    Initial implementation Uses eligibility,
                                                relevance, location fit,
                                                evidence coverage, and
                                                field completeness.

  SQLite persistence     Initial implementation Stores opportunities and
                                                application
                                                status/history; schema
                                                version 1.

  Application            Initial API            User-managed status
  checklist/tracking                            updates; does not submit
                                                applications.

  Frontend dashboard     Not implemented        No tracked frontend
                                                implementation is
                                                documented.

  Resume/cover-letter    Planned                Not confirmed as
  generation                                    implemented.

  Automated application  Not implemented        Any future submission must
  submission                                    require explicit user
                                                approval.

  Production deployment  Not verified           Prototype is not
                                                production-ready.
  ------------------------------------------------------------------------

## Architecture

``` text
Candidate profile + search request
                |
                v
       Discovery planning
                |
                v
        DDGS web discovery
                |
                v
 Candidate parsing and triage
                |
                v
    URL matching and deduplication
                |
                v
     Individual page retrieval
                |
                v
      HTML/PDF text extraction
                |
          +-----+-----+
          |           |
          v           v
   Deterministic   LLM-based
   metadata parse  extraction
          |           |
          +-----+-----+
                |
                v
   Evidence validation and merge
                |
                v
     Eligibility assessment
                |
                v
     Explainable opportunity rank
                |
                v
        Local SQLite store
                |
          +-----+------+
          |            |
          v            v
   Application     Status history
    checklist      and tracking
```

The current workflow is a bounded Python service behind the API, not a
fully expanded multi-agent LangGraph. Listing-page URL resolution, live
throughput, and full-source authenticity checks require broader
validation.

### Extraction strategy

-   Deterministic parsing handles explicit labels and constrained
    patterns.
-   LLM extraction handles semantic information such as
    responsibilities, eligibility explanations, and skills.
-   The outputs are reconciled; deterministic source-backed values take
    precedence for fields they reliably parse.
-   Every populated field should have traceable source evidence.
-   Unknown scalar fields remain `None`; missing list fields remain
    empty lists.
-   Posting age must not be confused with internship duration.
-   A monetary amount somewhere on a page does not prove a guaranteed
    stipend.

Evidence checks reduce unsupported claims but do not prove employer
authenticity or guarantee semantic correctness.

## Technology stack

  Layer                 Technology                Role
  --------------------- ------------------------- ---------------------------------
  Language              Python                    Backend and agents
  API                   FastAPI                   HTTP API
  Agent orchestration   LangGraph                 Discovery planning graph
  Local inference       Ollama                    Local LLM runtime
  Local model           `qwen2.5:3b`              Current development model
  Cloud fallback        Google Gemini API         Optional fallback
  Validation            Pydantic                  Structured schemas
  Web discovery         DDGS                      Search discovery
  HTTP                  HTTPX                     Page retrieval
  HTML                  Beautiful Soup            HTML parsing
  PDF                   PyMuPDF                   PDF extraction
  Database              SQLite                    Initial local persistence
  OS                    Windows 11 / PowerShell   Current development environment

Development hardware: 16 GB RAM and NVIDIA RTX 3050 Ti with 4 GB VRAM.
Model suitability depends on model size, quantization, context length,
and concurrency.

**Privacy:** NEXORA is local-first, not necessarily offline. When Gemini
fallback is invoked, relevant prompt content is sent to the configured
external provider. Avoid sending sensitive candidate data unless
necessary and authorized.

## Repository structure

This is a partial path map, not a complete repository inventory:

``` text
NEXORA/
├── backend/
│   ├── .venv/                         # Local virtual environment; do not commit
│   ├── app/
│   │   ├── agents/
│   │   │   └── opportunity_extraction_agent.py
│   │   ├── schemas/
│   │   │   └── opportunity.py
│   │   └── services/
│   │       ├── document_extraction_service.py
│   │       ├── linkedin_link_service.py
│   │       ├── linkedin_metadata_parser.py
│   │       └── listing_parser.py
│   ├── scripts/
│   │   └── test_linkedin_metadata_parser.py
│   ├── requirements.txt
│   ├── .env.example
│   └── .env                            # Local secrets; never commit
└── data/
    └── discovery_runs/                 # Local discovery/extraction artifacts
```

Additional discovery, LLM, candidate integration, persistence,
eligibility, ranking, API, and testing modules exist. Consult the
checkout for the complete current structure.

## Requirements

-   Python compatible with dependencies in `backend/requirements.txt`.
    Current development uses Python 3.14.7; verify dependency
    compatibility in a fresh environment.
-   Ollama installed and running.
-   `qwen2.5:3b` available locally, or another configured model.
-   Network access for DDGS, public vacancy retrieval, and optional
    Gemini fallback.
-   Gemini API key only if cloud fallback is enabled.

## Local setup --- Windows PowerShell

``` powershell
cd D:\Projects\NEXORA\backend

# Activate the existing virtual environment
.\.venv\Scripts\Activate.ps1

# For a fresh environment, use these instead:
# python -m venv .venv
# .\.venv\Scripts\Activate.ps1

python --version
python -m pip install --upgrade pip
pip install -r requirements.txt

# Verify Ollama and download the model if needed
ollama list
ollama pull qwen2.5:3b
```

Create `backend/.env` using `backend/.env.example` as the template.
Example development settings:

``` dotenv
LLM_PRIMARY_PROVIDER=ollama
LLM_FALLBACK_PROVIDER=gemini
OLLAMA_MODEL=qwen2.5:3b

# Set a model supported by the configured Gemini integration.
# GEMINI_MODEL=<supported-model-name>
# GEMINI_API_KEY=<your-key>
```

The application's settings and `.env.example` are authoritative if
configuration names differ. Never commit `.env`, credentials, tokens,
private application data, or scraped pages containing personal
information.

## Run the API

From `backend/` with the virtual environment activated:

``` powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

-   API base: `http://127.0.0.1:8000`
-   OpenAPI documentation: `http://127.0.0.1:8000/docs`

The workflow endpoint accepts a `user_request`, optional
`candidate_profile`, and `max_results` from 1 to 10.

The SQLite database defaults to `backend/data/nexora.sqlite3`. Set
`NEXORA_DB_PATH` to choose another path.

## API overview

  ------------------------------------------------------------------------------------------
  Method            Route                                             Purpose
  ----------------- ------------------------------------------------- ----------------------
  `POST`            `/api/workflow/run`                               Run bounded
                                                                      discovery-to-ranking
                                                                      workflow.

  `GET`             `/api/opportunities`                              Retrieve persisted
                                                                      opportunities.

  `GET`             `/api/opportunities/{id}/application-checklist`   Retrieve an
                                                                      application checklist.

  `GET`             `/api/applications`                               List application
                                                                      tracking records.

  `POST`            `/api/applications`                               Create an application
                                                                      tracking record.

  `PATCH`           `/api/applications/{id}`                          Update an application
                                                                      tracking record.
  ------------------------------------------------------------------------------------------

Consult `/docs` for exact request and response schemas.

When `NEXORA_API_TOKEN` is configured, `/api/` requests require the
corresponding bearer token. Otherwise, only loopback clients are
allowed. Role-based authorization is not implemented. For remote use,
configure a strong token and a trusted TLS-terminating proxy; do not
expose the development server directly to the public internet.

## Evidence, source credibility, and verification model

NEXORA keeps these questions separate:

1.  **Was the document fetched and parsed?** (`fetch_status`,
    `extraction_status`)
2.  **Is a field supported by source evidence?** (field-level evidence
    validation)
3.  **Has the vacancy or employer been independently verified?**
    (`verification_status`)

A successful HTTP fetch does not establish that a vacancy is genuine or
active. A valid quotation does not prove employer authenticity or
guarantee that every semantic interpretation is correct.

Eligibility is an assessment of stated requirements against supplied
candidate data; it is not a hiring prediction. Ranking is a relative
score under configured factors, not a guarantee of selection.

## Testing and validation

Run commands from `backend/` with the virtual environment activated.

### LinkedIn metadata regression

``` powershell
python -m compileall app\services\linkedin_metadata_parser.py scripts\test_linkedin_metadata_parser.py
python scripts\test_linkedin_metadata_parser.py
```

Latest reported result:

``` text
ALL REGRESSION ASSERTIONS PASSED
```

Previously tested saved examples:

  Organization           Duration      Stipend
  ---------------------- ------------- ---------------------------------
  Blue Machines AI       3--6 Months   Unknown
  Crossing Infotech AI   1--3 months   INR 15,500--16,500 per month
  Crossing Infotech ML   1--3 months   INR 15,500--16,500 per month
  Devryxa                3 Months      Performance-based, up to ₹7,500

These are parser regression observations, not independent verification
that vacancies remain open or that details are current.

### Workflow replay tests

``` powershell
python scripts/test_platform_workflow.py
python scripts/test_end_to_end_pipeline.py
```

These use saved datasets and mocked dependencies where configured. They
are repeatable integration checks, not substitutes for live accuracy,
throughput, or security testing.

A process that exits without an exception is not necessarily a
successful extraction. Evaluate field completeness, evidence validity,
correctness, and failure rates separately.

## Security and privacy

The document retrieval service currently includes:

-   HTTP(S)-only URL handling and rejection of embedded URL credentials.
-   DNS resolution checks rejecting non-global IP destinations.
-   Per-hop redirect validation and a redirect limit.
-   Bounded HTTP timeouts and an 8 MiB download limit.
-   A 100,000-character extracted-text limit.
-   HTML/PDF parsing with section/page references.

These are safeguards, not a complete security guarantee. DNS checks
before the HTTP request do not eliminate DNS rebinding or
connection-time resolution risks. PDF parsing can still consume
significant CPU or memory. Role-based authorization, database
encryption, and a mature migration strategy are not implemented.
Workflow requests are synchronous; application-level LLM deadlines and
resumable jobs remain future work.

Treat retrieved pages, PDFs, and search snippets as **untrusted data**.
They must never override system instructions, access credentials or
local files, change tool permissions, execute arbitrary commands, or
submit applications. Respect website terms and access restrictions; do
not bypass authentication or anti-bot protections.

Candidate profiles may contain personal information. Store only what is
necessary, restrict access, avoid logging sensitive fields, and do not
send candidate data to cloud model providers unless the user has
knowingly enabled that behavior and it is necessary.

## Known limitations

1.  Search coverage depends on DDGS and public-source discoverability;
    it is not exhaustive.
2.  Website layout changes can break parsers.
3.  Some platforms may expose incomplete or login-gated content.
4.  Evidence validation does not establish vacancy authenticity.
5.  Eligibility rules are conservative and may require human review.
6.  Ranking is an initial deterministic score, not a trained model.
7.  Live batch throughput and long-running reliability are not
    established.
8.  A frontend dashboard is not implemented in the documented project
    state.
9.  Resume/cover-letter generation is planned, not confirmed as
    implemented.
10. Application tracking is user-managed; the system does not submit
    applications.
11. Production deployment, observability, encryption, role-based
    authorization, and comprehensive security testing are not verified.

## Development roadmap

### Phase 1 --- Discovery and extraction

-   [x] Configure Ollama primary and Gemini fallback.
-   [x] Implement discovery planning and DDGS search.
-   [x] Implement candidate parsing, matching, triage, and
    deduplication.
-   [x] Implement bounded HTML/PDF extraction.
-   [x] Implement LinkedIn vacancy link resolution.
-   [x] Implement deterministic LinkedIn metadata extraction and
    regression tests.
-   [x] Integrate deterministic and LLM extraction with field-level
    provenance.
-   [x] Reject unsupported claims and distinguish conditional
    compensation.
-   [ ] Expand live validation across more sources and page layouts.
-   [ ] Measure field-level precision and recall using labeled data.

### Phase 2 --- Candidate intelligence

-   [x] Add initial candidate-specific eligibility rules.
-   [x] Add initial explainable ranking factors.
-   [ ] Expand candidate profile management and validation.
-   [ ] Add configurable preferences and hard constraints.
-   [ ] Improve ambiguous eligibility explanations.
-   [ ] Evaluate ranking against reviewed examples.

### Phase 3 --- Reliability and data

-   [x] Add initial SQLite opportunity persistence.
-   [x] Add initial application status history.
-   [ ] Expand migrations and backup/restore procedures.
-   [ ] Add resumable background workflows and bounded retries.
-   [ ] Add application-level LLM deadlines and provider budgets.
-   [ ] Improve observability and diagnostics.

### Phase 4 --- Application assistant

-   [ ] Build the React/TypeScript dashboard.
-   [ ] Add saved searches, filters, and opportunity detail views.
-   [ ] Add user-reviewed resume and cover-letter generation.
-   [ ] Add deadline reminders and application checklists.
-   [ ] Add optional email integration with explicit authorization.
-   [ ] Keep external application submissions under user approval.

### Phase 5 --- Security and deployment

-   [ ] Harden URL retrieval against DNS rebinding and unsafe redirects.
-   [ ] Add role-based authorization where required.
-   [ ] Add data retention, deletion, and encryption controls.
-   [ ] Add prompt-injection and malicious-document tests.
-   [ ] Add deployment automation, health checks, monitoring, and
    alerting.
-   [ ] Complete live load, reliability, and security testing before
    production claims.

## Contribution guidelines

1.  Inspect existing implementation and tests before changing code.
2.  Keep changes focused; avoid unnecessary rewrites.
3.  Preserve source provenance and field-level evidence.
4.  Add regression tests for parser, extraction, eligibility, and
    workflow changes.
5.  Never commit `.env`, API keys, tokens, local databases, or private
    candidate data.
6.  Document new environment variables and operational requirements.
7.  Report what was tested and what remains unverified.

Recommended development loop:

``` text
Inspect -> Plan -> Implement a small change -> Test -> Inspect outputs -> Integrate
```

## License

No repository license has been verified in the supplied project
documentation. Until a license is added, do not assume the project is
open source or that redistribution is permitted.

------------------------------------------------------------------------

**NEXORA AI --- Discover intelligently. Verify with evidence. Apply with
control.**
