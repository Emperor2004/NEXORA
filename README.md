# NEXORA AI

**Local-first, evidence-grounded internship discovery and intelligence platform**

> **Status: Active development / prototype.** Discovery, document extraction, and LinkedIn parsing components have been implemented and tested in isolation. End-to-end eligibility assessment, application management, persistence, and production deployment are not yet verified as complete.

NEXORA is a multi-agent AI platform intended to help students discover internships, examine original vacancy announcements, assess eligibility, and manage applications. Its architecture combines deterministic parsing with local language-model extraction, with an optional cloud-model fallback. The project's core principle is **traceable evidence over plausible guesses**: missing stipend, duration, or eligibility information should remain unknown until supported by source material.

## Objectives

- Discover relevant research and industry internships, including opportunities published by government institutions, universities, and private organizations.
- Distinguish search-result snippets, listing pages, programme information, and individual vacancy announcements.
- Fetch and parse public HTML and PDF announcements while retaining source context.
- Extract titles, organizations, locations, work arrangements, compensation, duration, requirements, and application information.
- Preserve evidence quotations and distinguish unverified opportunities from verified ones.
- Eventually evaluate candidate-specific eligibility and track applications without silently inventing facts.

## Current capabilities

| Component | Status | Notes |
| --- | --- | --- |
| LLM provider service | Implemented; fallback tested | Ollama primary; Gemini fallback configured in the development environment. |
| Discovery planning agent | Implemented | Produces structured discovery plans and search constraints. |
| LangGraph discovery node | Implemented | Full end-to-end graph not yet verified. |
| Web discovery | Implemented; tested | Uses DDGS; discovery runs have produced candidate search results. |
| Candidate integration and deduplication | Implemented | Exact integration behavior should be checked against current scripts. |
| Candidate quality triage | Implemented | Three-tier triage is reported in development tests. |
| HTML/PDF retrieval and text extraction | Implemented | Includes size/redirect limits and public-address checks. |
| LinkedIn listing parser | Implemented | Parses candidate entries from listing-page text. |
| LinkedIn vacancy link matching | Implemented | Finds and normalizes individual `/jobs/view/` links. |
| Individual vacancy fetching | Implemented | Uses the document extraction service. |
| Deterministic LinkedIn metadata parser | Implemented; regression-tested | Extracts title, organization, location, work mode, employment type, duration, stipend, and payment-related fields. |
| Evidence-grounded LLM extraction | Implemented in isolation | Validates source quotations; reconciliation with deterministic parser remains pending. |
| Field-level conflict reconciliation | **Planned** | Do not silently overwrite competing values. |
| Eligibility assessment | **Planned / unverified** | Candidate-specific decision engine not established from inspected files. |
| Application management | **Planned / unverified** | Tracking and automation are not yet established from inspected files. |
| SQLite persistence | **Planned / partially implemented** | Schema/migrations not yet inspected. |
| Production deployment | **Not verified** | Prototype should not be described as production-ready. |

## Architecture

```text
Student requirements / search request
                 |
                 v
       Discovery planning agent
                 |
                 v
        DDGS web discovery
                 |
                 v
      Candidate extraction + triage
                 |
                 v
       Deduplication / matching
                 |
                 v
     Public vacancy URL resolution
                 |
                 v
      HTML/PDF document extraction
                 |
          +------+------+
          |             |
          v             v
 Deterministic       LLM-based
 metadata parser     extraction
          |             |
          +------+------+
                 |
                 v
    Evidence-aware reconciliation
           [NOT YET BUILT]
                 |
                 v
      Opportunity records / store
        [IN DEVELOPMENT]
                 |
          +------+------+
          |             |
          v             v
 Eligibility       Application
 assessment        management
  [PLANNED]         [PLANNED]
```

**Important:** The diagram describes the intended integrated architecture, not a claim that every stage already executes end-to-end.

### Extraction strategy

The deterministic LinkedIn parser uses labeled fields and constrained regular expressions. The LLM extraction agent uses a Pydantic schema and requests verbatim evidence quotations. Its current evidence validation checks whether quotations appear in the supplied source text and removes claims without field-associated quotations. This does **not yet prove semantic support** for every accepted claim. A future reconciliation layer must verify field/value/evidence consistency, track extractor provenance, and flag disagreements.

Unknown scalar fields should remain `None`; missing list fields should remain empty lists. Posting age must not be treated as internship duration. A monetary amount appearing somewhere on a page is not sufficient to prove that an internship offers a guaranteed stipend.

## Technology stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.14.7 (current development environment) |
| API | FastAPI |
| Agent orchestration | LangGraph (partially integrated) |
| Local model runtime | Ollama |
| Primary local model | `qwen2.5:3b` |
| Fallback LLM | Gemini (configured and connection-tested) |
| Validation | Pydantic |
| Web search | DDGS |
| HTTP | HTTPX |
| HTML processing | Beautiful Soup |
| PDF processing | PyMuPDF |
| Database | SQLite (planned / partially implemented) |
| OS | Windows 11 / PowerShell |

Development hardware: 16 GB RAM and NVIDIA RTX 3050 Ti with 4 GB VRAM. The architecture is designed to be local-first, but **Gemini fallback sends relevant prompts to an external provider when invoked**.

## Repository structure

The following is a **partial, verified path map**, not a complete repository inventory:

```text
NEXORA/
└── backend/
    ├── .venv/                          # Local virtual environment
    ├── app/
    │   ├── agents/
    │   │   └── opportunity_extraction_agent.py
    │   ├── schemas/
    │   │   └── opportunity.py
    │   └── services/
    │       ├── document_extraction_service.py
    │       ├── linkedin_link_service.py
    │       ├── linkedin_metadata_parser.py
    │       └── listing_parser.py
    └── scripts/
        └── test_linkedin_metadata_parser.py
```

Additional discovery, LLM, candidate integration, and testing modules exist in the development workflow but have not all been inspected for this README. The opportunity extraction agent imports `app.services.llm_service`; that module must be present for LLM extraction to work.

## Local setup (Windows PowerShell)

### Prerequisites

- Python compatible with the project's installed dependencies (currently developed with Python 3.14.7).
- Ollama installed and running.
- Network access for DDGS, public vacancy retrieval, and optional Gemini fallback.
- Project dependencies and API credentials as required by the local implementation.

```powershell
cd D:\Projects\NEXORA\backend

# Activate the existing virtual environment
.\.venv\Scripts\Activate.ps1

# Confirm interpreter
python --version

# Check that Ollama is installed and the local model is available
ollama list

# Fetch the model if it is not already installed
ollama pull qwen2.5:3b
```

For a fresh checkout, create an environment with `python -m venv .venv`, activate it, and install dependencies using the repository's **actual** dependency manifest. A complete manifest has not been inspected, so no unverified installation command is provided here.

### Configuration

The development setup uses a `backend/.env` file for LLM provider selection. Previously exercised settings include:

```dotenv
LLM_PRIMARY_PROVIDER=ollama
LLM_FALLBACK_PROVIDER=gemini
OLLAMA_MODEL=qwen2.5:3b
# GEMINI_MODEL=<model supported by the configured provider>
# GEMINI_API_KEY=<set locally; never commit>
```

These are illustrative configuration keys from development, **not a verified complete `.env.example`**. Confirm actual names and model availability in `app/services/llm_service.py`. Never commit `.env`, credentials, private application data, or scraped pages containing personal information.

### Running the API

FastAPI is part of the project, but the current application entry point and route layout were not included in the inspected files. Inspect the backend's app entry point before selecting a `uvicorn` command; do not assume `app.main:app` exists.

## Testing

### Confirmed LinkedIn metadata regression test

From the backend directory with the environment activated:

```powershell
python -m compileall app\services\linkedin_metadata_parser.py scripts\test_linkedin_metadata_parser.py
python scripts\test_linkedin_metadata_parser.py
```

Latest reported result:

```text
ALL REGRESSION ASSERTIONS PASSED
```

Previously tested examples include:

| Organization | Extracted duration | Extracted stipend |
| --- | --- | --- |
| Blue Machines AI | 3–6 Months | Unknown |
| Crossing Infotech AI | 1–3 months | INR 15,500 to INR 16,500 per month |
| Crossing Infotech ML | 1–3 months | INR 15,500 to INR 16,500 per month |
| Devryxa | 3 Months | Performance-based, up to ₹7,500 |

These are **parser regression observations**, not independently verified live vacancy details or proof that the positions are still open.

### Pending integration validation

Before connecting deterministic extraction to LLM extraction:

1. Inspect the current extraction agent, metadata parser, schema, and calling scripts.
2. Define evidence provenance and conflict structures without breaking existing consumers.
3. Validate exact supporting text for every populated field, including candidate-derived values.
4. Keep document fetch/extraction status separate from source authenticity verification.
5. Test all ten previously fetched individual vacancy pages.
6. Run existing regression tests, then integrate into the main discovery pipeline.

## Security and reliability

The document retrieval service currently includes:

- HTTP(S)-only URLs and rejection of embedded URL credentials.
- DNS resolution checks rejecting non-global IP destinations.
- Per-hop redirect validation with a redirect limit.
- Bounded HTTP timeouts and an 8 MiB download limit.
- An extracted-text limit of 100,000 characters.
- HTML and PDF parsing with section/page references.

**Known limitation:** DNS checks before the HTTP request do not by themselves eliminate DNS rebinding or connection-time resolution risks. The service should be hardened and security-tested before accepting arbitrary untrusted URLs in a deployed environment. Download size limits also do not guarantee bounded CPU or memory consumption during PDF parsing.

Treat downloaded vacancy text as **untrusted data**, not instructions. Never allow a vacancy page to control system prompts, tools, credentials, or application submissions. Comply with website terms and access restrictions; do not bypass authentication or anti-bot protections.

## Evidence and verification model

NEXORA aims to distinguish three different questions:

1. **Was the document fetched and parsed?** (`fetch_status`, `extraction_status`)
2. **Is a particular field supported by source evidence?** (field-level evidence validation)
3. **Is the vacancy or employer independently verified?** (`verification_status`)

A successful HTTP fetch does not establish that a vacancy is authentic or active. Likewise, a valid evidence quote does not automatically establish that the extracted interpretation is correct.

## Roadmap

- [x] Configure Ollama primary and Gemini fallback.
- [x] Implement discovery planning and DDGS search.
- [x] Implement candidate parsing, matching, and triage.
- [x] Implement HTML/PDF document extraction.
- [x] Implement LinkedIn vacancy link resolution.
- [x] Implement deterministic LinkedIn metadata extraction and initial regression tests.
- [ ] Integrate deterministic and LLM extraction with field-level provenance.
- [ ] Detect conflicts and reject unsupported stipend/duration claims.
- [ ] Validate reconciliation against all ten fetched vacancy pages.
- [ ] Finalize opportunity persistence and schema migrations.
- [ ] Implement candidate-specific eligibility assessment with explainable rules.
- [ ] Implement application tracking and reminders.
- [ ] Add API, integration, security, and regression test coverage.
- [ ] Verify deployment, observability, and operational safeguards.

## Project principles

**Evidence before inference.** Do not convert uncertainty into fabricated facts.

**Local-first, not necessarily offline.** Local inference is preferred; web discovery and fallback inference require network access.

**Human control.** Users should review eligibility decisions and application actions; automated submissions are not a verified capability.

**Incremental verification.** Implement, compile, test, inspect outputs, and only then integrate.

## License and contributions

No license or contribution policy has been verified. **Do not assume this repository is open source or grant redistribution rights until a license is added.**

---

*NEXORA AI — Intelligent internship discovery with traceable evidence.*
