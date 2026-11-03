# Agentic architecture implementation plan

This plan follows `NEXORA_AGENTIC_AI_ARCHITECTURE.md`. It reuses existing
services and distinguishes an integrated LLM agent from a deterministic
service. A profile or roadmap entry alone does not mean a role is implemented.

## Current role mapping

| Target role | Existing implementation | Status |
| --- | --- | --- |
| Supervisor / orchestrator | Typed LangGraph wrapper around `InternshipWorkflow` | Initial integration |
| Candidate profile | Pydantic request schema | Profile agent and durable versioning planned |
| Discovery planning | `DiscoveryAgent` | Integrated through typed task/result envelopes |
| Multi-source discovery | DDGS with modular source adapters | Deterministic service, no separate LLM agent |
| Source resolution and deduplication | URL normalization and workflow deduplication | Deterministic service, within-run identity only |
| Document retrieval | Bounded HTML/PDF retrieval service | Deterministic service |
| Opportunity extraction | Evidence-grounded extractor and LinkedIn metadata parser | Integrated through typed task/result envelopes |
| Verification and fraud risk | Verification and fraud-risk service | Initial deterministic assessment |
| Eligibility assessment | Eligibility rules service | Initial deterministic assessment |
| Ranking and recommendation | Ranking service | Initial deterministic scoring |
| Application preparation | None | Planned |
| Application tracking and monitoring | SQLite tracking API | Tracking exists; monitoring/reminders planned |

## Phased plan

### Phase A — agent foundation

**Dependencies:** Existing Pydantic v2, LangGraph, discovery planner,
extractor, workflow service, and LLM adapters.

**Files:** `backend/app/schemas/agent.py`, `backend/app/agents/registry.py`,
`backend/app/graph/state.py`, `backend/app/graph/nodes.py`,
`backend/app/graph/workflow.py`, `backend/app/services/agent_runtime.py`,
`backend/app/services/model_trace.py`, `backend/app/services/llm_service.py`,
and `backend/app/main.py`.

**Implemented in this increment:** Typed workflow state and task/result
envelopes; versioned profiles for the integrated supervisor, planner, and
extractor; input/output validation; provider allowlists, output-token and
client-timeout limits; bounded retries; task-local provider/model tracing;
and LangGraph wiring for discovery planning and the existing full workflow.
Each invocation uses an ephemeral in-memory checkpoint that can be inspected
during the invocation; it is not retained or resumable after the request ends.

**Risks and limits:** The main workflow remains synchronous. A supervisor
deadline can reject a late result but cannot cancel an already-running
synchronous stage. Provider token/cost usage is unavailable, so a usage-based
cost ceiling is not yet enforceable. Durable checkpoint persistence is
deferred to Phase F to avoid retaining candidate profile data before
retention controls exist.

**Acceptance checks:** `backend/scripts/test_agent_foundation.py` validates
registered profiles, task/result schemas, invalid and expired inputs, retry
limits, provider restrictions, discovery-graph tracing, and the supervisor's
workflow response contract and in-memory checkpoint snapshot. The offline
end-to-end replay and multi-source regression scripts also pass.

### Phase B — discovery and source intelligence

**Dependencies:** Phase A shared state and current source adapters.

**Files:** `backend/app/services/source_adapters.py`,
`backend/app/services/search_service.py`,
`backend/app/services/internship_workflow_service.py`, candidate schemas, and
source-resolution tests.

**Work:** Add validated candidate-profile and discovery-plan contracts,
source selection from plans, canonical URL/redirect records, deduplication
confidence, and durable provenance. Keep source-specific behavior in adapters
unless evaluation shows that independent reasoning is needed.

**Risks:** Website policy/layout changes and false duplicate matches. Ambiguous
identities must remain separate and go to review.

**Acceptance:** Offline fixtures cover each configured source family, original
and redirected URLs, duplicates, and ambiguous near-matches; source diversity
is visible in workflow reports.

### Phase C — retrieval, extraction, and trust

**Dependencies:** Phase B candidate/source identity contracts and existing
safe retrieval/extraction services.

**Files:** `document_extraction_service.py`, `opportunity_extraction_agent.py`,
`schemas/opportunity.py`, `verification_service.py`, the shared state, and
security/evidence fixtures.

**Work:** Add typed retrieval and verification reports, field conflict
preservation, source-level evidence references, and a review queue. Keep
fraud indicators separate from factual authenticity conclusions.

**Risks:** False-positive risk flags and overclaiming authenticity. Human
review remains required for uncertain or consequential trust decisions.

**Acceptance:** Fixtures cover official, third-party, expired, copied,
login-gated, conflicting, and malicious-document examples. Assertions verify
that unsupported claims are removed and risk conclusions retain quotations.

### Phase D — candidate intelligence

**Dependencies:** Phase C evidence and verification reports plus candidate
profile contracts.

**Files:** `schemas/workflow.py`, `eligibility_service.py`,
`ranking_service.py`, profile persistence, and labeled evaluation fixtures.

**Work:** Validate and version candidate facts/preferences; cite vacancy and
profile evidence per eligibility criterion; separate eligibility from
recommendation score; incorporate verification and risk warnings.

**Risks:** Incorrect rejection or ranking due to incomplete profiles and
ambiguous source criteria.

**Acceptance:** Labeled cases measure false-eligible and false-ineligible
rates, ranking stability, evidence coverage, and uncertainty handling.

### Phase E — application lifecycle

**Dependencies:** Validated candidate profile, opportunity evidence, and
approval gates from Phases C/D.

**Files:** New application-draft services/schemas, existing tracking API and
SQLite store, and later frontend integration.

**Work:** Prepare user-reviewed drafts using only approved candidate facts;
track deadlines/reminders and explicit status evidence. Do not send messages or
submit applications automatically.

**Risks:** Fabricated candidate claims or unauthorized external actions.

**Acceptance:** Drafts cite source facts, unsupported claims are rejected, and
tests prove no external send/submit occurs without explicit approval.

### Phase F — production hardening

**Dependencies:** Stable state schemas and completed workflow stages.

**Files:** Checkpoint/database configuration, migrations, URL retrieval,
authentication, logging/metrics, retention controls, deployment files, and
operational documentation.

**Work:** Add persistent graph checkpoints, resumable jobs, multi-user access
controls where required, backups/deletion, stronger SSRF protections, load
and security testing, and operational runbooks.

**Risks:** Persisting personal data or unsafe retrieval state; operational
claims exceeding measured evidence.

**Acceptance:** Recovery, retention, access-control, load, and security
criteria pass before any production-readiness claim.
