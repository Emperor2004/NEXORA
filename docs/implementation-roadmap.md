# NEXORA AI: Repository Audit and Roadmap

## Baseline observed before the current implementation increment

The repository contains a Python backend and saved development runs. The `frontend`, `models`, and `docs` directories have no tracked implementation at the time of this audit. The backend already has useful pieces for discovery planning, DDGS search, listing parsing, URL matching, public HTML/PDF extraction, LinkedIn metadata parsing, structured LLM extraction, evidence checks, and relevance triage.

At the audit baseline, these pieces were mostly invoked by scripts. The FastAPI app exposed health checks and discovery planning only. The LangGraph graph contained one planning node. There was no opportunity/application database, profile-aware eligibility evaluator, explainable ranking service, application progress API, or frontend.

Saved run data shows the current scale and failure modes: one search run produced 9 results; 5 of 9 documents were fetched with readable text; listing integration reduced 113 occurrences to 71 candidates; URL matching found 56 exact matches among 62 candidates, with 4 candidate records needing review and 2 without an exact match. A separate vacancy batch fetched and extracted 10 of 10 pages. These are historical fixture results, not current service-level guarantees.

The extraction path has recently been strengthened to combine deterministic LinkedIn fields with LLM extraction, validate field evidence and provenance, reject login-only pages, and classify conditional compensation. The existing run artifacts predate those protections and should not be treated as trusted records without reprocessing.

## Roadmap

### Phase 1 — Integrated discovery and verified opportunities

- Preserve and call the existing discovery, search, fetch, parser, and extraction services from one bounded workflow.
- Apply URL and result limits, per-record failure capture, deduplication, evidence validation, and explicit `not_independently_verified` status.
- Add candidate-profile eligibility decisions with conservative `eligible`, `ineligible`, and `needs_review` outcomes.
- Rank opportunities with visible, evidence-aware factors; do not turn unknowns into positive claims.
- Acceptance: fixture replay covers each stage, every returned factual claim has valid field-level evidence, and failed records do not stop the batch.

### Phase 2 — Local persistence and application tracking

- Add SQLite storage for opportunities, evidence, application records, and status history.
- Use stable identities and idempotent upserts; keep candidate profile data local and minimize retained personal data.
- Add user-controlled application checklist and status updates; do not submit applications automatically.
- Acceptance: restart-safe retrieval, deduplication, status transition history, and migration/version handling.

### Phase 3 — Application assistance and user interface

- Add user-reviewed resume/cover-letter assistance based only on candidate-provided facts and verified vacancy requirements.
- Build a frontend for discovery review, eligibility explanations, ranking, application preparation, and progress tracking.
- Acceptance: all generated content shows its source facts and requires review before export or submission.

### Phase 4 — Reliability, security, and cost controls

- Add resumable work queues, request deadlines, bounded retries, rate limits, and provider budgets.
- Harden URL fetching against DNS rebinding and test SSRF controls; treat vacancy text as untrusted prompt input.
- Add audit logging, data retention/export/delete controls, operational metrics, and security regression tests.
- Acceptance: repeatable load/failure tests and documented operational limits; no production-readiness claim until these pass.

## Current execution order

Initial Phase 1/2 implementation now exists: a bounded workflow service, conservative eligibility and ranking services, local SQLite opportunity/application storage, and user-controlled application status endpoints. Existing parsers and extraction behavior remain the source of truth; workflow and storage layers wrap them rather than replace them. Network discovery and vacancy fetching remain bounded, and application submission remains user-controlled.

Remaining acceptance work includes expanding live-source validation, adding migrations beyond the initial schema version and role-based API authorization, validating eligibility against labeled cases, and implementing the frontend and application-material assistance. The API currently requires a bearer token when `NEXORA_API_TOKEN` is configured and otherwise accepts loopback clients only.
