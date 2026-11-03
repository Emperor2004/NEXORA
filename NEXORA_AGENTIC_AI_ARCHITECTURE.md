# NEXORA AI --- Agentic AI Architecture & Multi-Agent Operating Specification

> **Purpose:** Define how NEXORA's specialist AI agents think,
> collaborate, share evidence, make decisions, and hand work to one
> another.
>
> **Architecture direction:** A coordinated, state-driven multi-agent
> system built with LangGraph, typed shared state, specialist agent
> profiles, deterministic services, and human approval checkpoints.
>
> **Implementation status:** This document describes the target
> architecture. It does not claim that all agents or workflows are
> already implemented.

------------------------------------------------------------------------

## 1. Mission

NEXORA is an AI-powered internship research and application assistant.
Its job is to discover internship opportunities across multiple sources,
retrieve original vacancy announcements, extract and verify information,
evaluate candidate eligibility, rank opportunities, prepare application
materials, and track application progress.

The system must optimize for:

1.  Opportunity relevance.
2.  Source traceability and evidence quality.
3.  Vacancy and employer legitimacy.
4.  Eligibility assessment accuracy.
5.  Explainable recommendations.
6.  Safe, user-controlled application workflows.
7.  Reliability, cost efficiency, and maintainability.

NEXORA must not optimize merely for the number of listings collected.

## 2. Recommended agent count

**Recommended target: 12 specialist agents, including one central
orchestrator.**

This is enough specialization to give each role a clear responsibility
without creating an unnecessarily large swarm. Source-specific crawlers
should normally be implemented as adapters/tools, not as separate LLM
agents. Add a new agent only when it has a distinct decision
responsibility, independent tools, a clear input/output contract, and
measurable value.

  ------------------------------------------------------------------------
                            \# Agent                 Primary
                                                     responsibility
  ---------------------------- --------------------- ---------------------
                             1 Supervisor /          Coordinates the
                               Orchestrator Agent    workflow, delegates
                                                     tasks, manages state,
                                                     retries, and human
                                                     approval gates.

                             2 Candidate Profile     Maintains and
                               Agent                 validates candidate
                                                     facts, preferences,
                                                     constraints, and
                                                     profile completeness.

                             3 Discovery Planning    Converts the user's
                               Agent                 request into search
                                                     plans, source
                                                     priorities, queries,
                                                     and constraints.

                             4 Multi-Source          Finds candidate
                               Discovery Agent       opportunities through
                                                     registered source
                                                     adapters and search
                                                     tools.

                             5 Source Resolution &   Resolves original
                               Deduplication Agent   vacancy URLs, groups
                                                     duplicate listings,
                                                     and maintains source
                                                     provenance.

                             6 Document Retrieval    Fetches permitted
                               Agent                 public pages and
                                                     documents and
                                                     prepares clean,
                                                     structured source
                                                     content.

                             7 Opportunity           Produces structured
                               Extraction Agent      vacancy fields with
                                                     field-level
                                                     quotations and source
                                                     locations.

                             8 Verification &        Checks
                               Fraud-Risk Agent      employer/vacancy
                                                     corroboration and
                                                     identifies
                                                     evidence-backed scam
                                                     indicators.

                             9 Eligibility           Compares explicit
                               Assessment Agent      vacancy requirements
                                                     with the candidate
                                                     profile and explains
                                                     gaps.

                            10 Ranking &             Scores and ranks
                               Recommendation Agent  opportunities using
                                                     transparent,
                                                     configurable factors.

                            11 Application           Prepares tailored
                               Preparation Agent     application documents
                                                     and responses using
                                                     verified candidate
                                                     facts.

                            12 Application Tracking  Tracks user-managed
                               & Monitoring Agent    application status,
                                                     deadlines, reminders,
                                                     and follow-up events.
  ------------------------------------------------------------------------

### Why not create one agent for every website?

A website adapter is usually a deterministic integration that knows how
to query or parse a particular source. It does not need independent
reasoning. For example, Internshala, Naukri, an official ministry page,
and an IIT careers page can each have a source adapter. The Multi-Source
Discovery Agent selects and coordinates these adapters.

Create separate source-specialist agents only if later measurements show
that a source family requires materially different reasoning, tools, or
policies. Do not multiply agents just to increase the agent count.

------------------------------------------------------------------------

## 3. What "each agent has its own brain" means

Each specialist must have an independent **Agent Profile**. An agent's
brain is not necessarily a separate model or a separate GPU process. It
is a controlled package of role-specific instructions, context, tools,
state, memory scope, output schema, and decision policy.

Every agent profile must define:

  -----------------------------------------------------------------------
  Element                             Meaning
  ----------------------------------- -----------------------------------
  Identity                            Unique agent name and version.

  Mission                             One narrow responsibility and
                                      measurable objective.

  System instructions                 Role-specific rules, boundaries,
                                      and priorities.

  Input contract                      Typed data the agent is allowed to
                                      receive.

  Output contract                     Pydantic model or other validated
                                      structured result.

  Tool permissions                    Explicit allowlist of tools and
                                      actions.

  Working context                     Relevant task data and upstream
                                      outputs.

  Private working memory              Temporary reasoning notes or
                                      task-local findings, not an
                                      unrestricted shared memory.

  Shared state access                 Explicit read/write permissions for
                                      canonical workflow fields.

  Model policy                        Preferred model, fallback model,
                                      temperature, token budget, and
                                      timeout.

  Decision policy                     Conditions for success,
                                      uncertainty, rejection, retry, or
                                      human review.

  Audit trail                         Inputs, outputs, tool calls,
                                      evidence references,
                                      model/provider, and timestamps.
  -----------------------------------------------------------------------

### Separate role brains, shared facts

Agents should have independent instructions and task context, but they
must not maintain conflicting copies of canonical opportunity facts.

Use this rule:

-   **Private agent workspace:** temporary analysis and task-specific
    notes.
-   **Shared workflow state:** canonical facts, source references,
    evidence, statuses, and decisions.
-   **Persistent database:** durable records and history.
-   **Agent memory:** only approved, scoped, useful information; never
    an uncontrolled dump of previous conversations or scraped pages.

A specialist should not silently overwrite another agent's verified
result. Conflicts must be recorded and routed for reconciliation or
human review.

### Model independence

Different agents may use different models, but they do not need separate
models by default.

Recommended routing:

-   Deterministic Python services for URL normalization, deduplication,
    explicit metadata parsing, scoring arithmetic, schema checks, and
    policy enforcement.
-   Local Ollama model for routine extraction, classification, and
    low-cost reasoning.
-   Gemini fallback for selected complex tasks when enabled and
    permitted.
-   Embedding model for semantic matching and retrieval.
-   Human review for high-impact or ambiguous decisions.

The orchestrator chooses a provider according to task complexity,
privacy requirements, latency, cost budget, and provider availability.
Cloud fallback must be explicit and auditable.

------------------------------------------------------------------------

## 4. Detailed agent specifications

### Agent 1 --- Supervisor / Orchestrator

**Mission:** Own the workflow, not the domain-specific conclusions.

**Responsibilities** - Accept a user request and create a workflow
run. - Load the relevant candidate profile and preferences. - Build and
execute the LangGraph state machine. - Delegate work to specialist
agents and deterministic services. - Run independent branches in
parallel where safe. - Enforce timeouts, retry limits, provider budgets,
and rate limits. - Route failures and conflicts to recovery or human
review. - Ensure no application is submitted without explicit
approval. - Produce a concise workflow summary and audit record.

**Tools:** LangGraph runtime, state store, task scheduler, agent
registry, run logger.

**Must not:** Invent vacancy facts, decide authenticity without
verification evidence, or bypass an approval gate.

**Output:** Workflow status, agent task outcomes, unresolved issues,
final run summary.

### Agent 2 --- Candidate Profile Agent

**Mission:** Maintain a validated representation of the candidate and
their preferences.

**Responsibilities** - Structure education, degree, semester,
institution, CGPA, skills, projects, experience, availability, location
preferences, stipend preferences, duration, and research interests. -
Distinguish user-provided facts from inferred or incomplete
information. - Identify missing or contradictory profile fields. - Ask
for clarification only when a missing fact materially affects
eligibility or ranking. - Version profile changes and retain provenance.

**Tools:** Candidate profile database, profile validation schemas.

**Must not:** Invent qualifications, skills, achievements, work
experience, or academic results.

**Output:** Versioned `CandidateProfile`, preference constraints,
profile completeness warnings.

### Agent 3 --- Discovery Planning Agent

**Mission:** Convert a broad internship request into a search strategy.

**Responsibilities** - Generate search queries and keyword variants. -
Identify target source categories and domains. - Separate hard
constraints from preferences. - Plan date, duration, location, stipend,
and research-area filters. - Avoid repeatedly issuing equivalent
searches. - Estimate discovery budget and prioritize high-value sources.

**Tools:** Search query builder, source registry, candidate preferences.

**Output:** `DiscoveryPlan` with queries, target sources, constraints,
exclusions, and rationale.

### Agent 4 --- Multi-Source Discovery Agent

**Mission:** Find candidate internship listings across a diverse set of
sources.

**Target source families** - Official government internship portals and
ministry websites. - ISRO, DRDO, CSIR, and other research organizations'
official pages. - IITs, IISc, NITs, IISERs, universities, and laboratory
websites. - Direct employer career pages and company research pages. -
Internship platforms such as Internshala. - General job platforms such
as Indeed, Naukri, Foundit, Wellfound, and LinkedIn. - Search engines
and permitted public feeds.

**Responsibilities** - Select adapters based on the discovery plan. -
Search multiple source families rather than relying on one platform. -
Preserve the source platform, original URL, query, discovery timestamp,
and snippet. - Respect rate limits, terms, robots policies, and access
restrictions. - Return candidate records, not claims of verified
vacancies.

**Tools:** DDGS or approved search APIs, source adapters, permitted HTTP
retrieval.

**Must not:** Treat a search result or platform reputation as proof of
legitimacy.

**Output:** `DiscoveryCandidate[]` with source provenance and discovery
metadata.

### Agent 5 --- Source Resolution & Deduplication Agent

**Mission:** Establish the relationship between listings, canonical
vacancies, and original publishers.

**Responsibilities** - Normalize URLs and remove tracking parameters
where safe. - Follow permitted redirects and record the redirect
chain. - Identify canonical employer or institution URLs. - Match the
same vacancy across multiple platforms. - Detect copied or
near-duplicate descriptions. - Preserve all discovery sources while
selecting a canonical source when justified. - Avoid merging different
roles merely because titles or organizations look similar.

**Tools:** URL normalization, redirect resolver, similarity service,
duplicate index.

**Output:** `SourceResolution` and `OpportunityIdentity` records with
match confidence and provenance.

### Agent 6 --- Document Retrieval Agent

**Mission:** Retrieve permitted public source content safely and
consistently.

**Responsibilities** - Fetch public HTML and PDF pages. - Apply URL
safety checks, redirect validation, download limits, timeouts, and
content-type checks. - Extract headings, sections, paragraphs, tables,
and PDF page references. - Remove irrelevant boilerplate while
preserving the original raw content and extraction trace. - Detect login
walls, access denials, empty pages, and unsupported formats. - Mark
incomplete or blocked retrievals clearly.

**Tools:** HTTPX, Playwright where permitted, BeautifulSoup,
Trafilatura, PyMuPDF, document extraction service.

**Must not:** Bypass login, CAPTCHA, paywalls, or anti-bot protections.

**Output:** `RetrievedDocument` with original URL, content hash, fetch
status, extracted text, section/page references, and retrieval metadata.

### Agent 7 --- Opportunity Extraction Agent

**Mission:** Convert retrieved vacancy content into a structured
opportunity record.

**Fields may include** - Role title and organization. - Location and
work mode. - Employment type. - Internship duration and start/end
dates. - Stipend and compensation conditions. - Eligibility
requirements. - Required/preferred skills. - Responsibilities and
research areas. - Deadline and application method. - Official
application URL and contact details.

**Responsibilities** - Use deterministic parsing for explicit labels and
constrained patterns. - Use an LLM for semantic fields. - Require
field-level evidence quotations and source locations. - Keep missing
scalar values null and missing lists empty. - Distinguish posting age
from internship duration. - Preserve conflicting values instead of
silently choosing one. - Mark uncertain or unsupported fields for
review.

**Tools:** Existing LinkedIn metadata parser, general extraction
parsers, Pydantic schemas, local LLM, optional cloud fallback.

**Output:** `OpportunityExtraction` with per-field provenance,
confidence/validation status, and unresolved conflicts.

### Agent 8 --- Verification & Fraud-Risk Agent

**Mission:** Assess the legitimacy signals of a specific vacancy and
employer using evidence.

**Separate assessments** 1. **Source credibility:** Is the
hosting/discovery source identifiable and appropriate? 2. **Employer
corroboration:** Does the claimed organization have a matching official
identity and domain? 3. **Vacancy corroboration:** Is the specific role
supported by an original employer/institution announcement? 4.
**Application destination:** Does the application URL appear consistent
with the organization and process? 5. **Fraud-risk indicators:** Are
there suspicious claims or behaviors?

**Signals to investigate** - Employer/domain mismatch or
impersonation. - Recruiter email inconsistent with the official
organization domain. - Requests for registration, processing, training,
security, or placement fees. - Unrealistic or unsupported compensation
promises. - Unofficial forms, suspicious redirects, shortened links, or
excessive personal-data requests. - Copied vacancy descriptions or
repeated contact details. - Urgency, guaranteed selection, or other
pressure tactics. - Inconsistent dates, organization names, addresses,
and role details.

**Responsibilities** - Search for independent corroboration using
permitted sources. - Record evidence for each positive and negative
signal. - Distinguish `verified`, `partially_verified`, `unverified`,
`suspicious`, and `needs_human_review` states according to a documented
policy. - Explain why a risk flag was raised. - Avoid unsupported
accusations; risk indicators are not proof of fraud. - Escalate
ambiguous or high-impact cases to human review.

**Tools:** Official-domain lookup, search, source registry, URL
analysis, email-domain checks, duplicate-content service, risk rules.

**Must not:** Declare a listing legitimate merely because it appears on
a famous platform. Do not label an employer fraudulent without adequate
evidence.

**Output:** `VerificationReport` with separate source, employer,
vacancy, and application-destination assessments, evidence references,
risk flags, and review recommendation.

### Agent 9 --- Eligibility Assessment Agent

**Mission:** Compare explicit opportunity requirements with the
candidate profile.

**Responsibilities** - Evaluate degree, branch, semester/year, CGPA,
skills, experience, location, duration, citizenship or other stated
criteria where applicable. - Separate hard eligibility requirements from
preferences. - Return `eligible`, `potentially_eligible`, `ineligible`,
or `needs_review`. - Cite the exact vacancy evidence and
candidate-profile facts used. - Explain unmet requirements and missing
candidate information. - Avoid converting an unstated requirement into a
rejection.

**Tools:** Deterministic rules engine, candidate profile, structured
opportunity data, evidence store.

**Must not:** Predict selection probability or infer requirements not
stated by the source.

**Output:** `EligibilityAssessment` with per-criterion outcomes,
explanations, and evidence references.

### Agent 10 --- Ranking & Recommendation Agent

**Mission:** Rank opportunities transparently after eligibility and risk
assessment.

**Possible factors** - Hard eligibility outcome. - Research/role
relevance. - Skills alignment. - Source and vacancy verification
status. - Evidence completeness. - Stipend and compensation clarity. -
Duration and timing fit. - Location/work-mode fit. - Deadline urgency. -
Candidate-configured priorities.

**Responsibilities** - Apply configurable weights and hard exclusions. -
Keep eligibility and recommendation score separate. - Avoid rewarding
suspicious or unverified listings merely for a high stipend. - Explain
the factors contributing to each rank. - Provide a reason for exclusions
or low rankings.

**Tools:** Deterministic scoring service, candidate preferences,
eligibility reports, verification reports.

**Output:** `OpportunityRanking[]` with score breakdown, rank,
recommendation rationale, and warnings.

### Agent 11 --- Application Preparation Agent

**Mission:** Help the candidate prepare accurate, tailored application
materials.

**Responsibilities** - Prepare a resume version, cover letter, statement
of purpose, email draft, or application response as requested. - Use
only verified candidate profile facts and user-approved
project/experience details. - Tailor content to the vacancy's stated
requirements. - Identify missing documents or unanswered questions. -
Provide a checklist and source link. - Require user review before any
external submission.

**Tools:** Approved candidate documents, document generation service,
opportunity record, application checklist.

**Must not:** Fabricate skills, experience, publications, grades, or
achievements. Must not submit applications or send emails without
explicit user approval.

**Output:** Draft application package, checklist, missing-information
report, approval request.

### Agent 12 --- Application Tracking & Monitoring Agent

**Mission:** Maintain user-controlled application progress and notify
the user about relevant events.

**Responsibilities** - Track saved, preparing, ready-to-submit,
submitted, assessment, interview, rejected, offered, and withdrawn
states as supported by the user's workflow. - Record submission date and
user-provided confirmation. - Track deadlines and follow-up dates. -
Monitor authorized email or portal sources only when the user connects
them and grants permission. - Create reminders and summarize changes. -
Preserve a complete status history.

**Tools:** Application database, scheduler, notification service,
authorized email connector.

**Must not:** Claim an application was submitted unless the user or an
authorized integration confirms it.

**Output:** Updated application record, event history, reminders, and
status summaries.

------------------------------------------------------------------------

## 5. How the agents coordinate

Use **LangGraph as the control plane**. Do not let agents freely message
each other without a shared contract. All coordination should happen
through typed tasks, explicit handoffs, shared state, and logged
decisions.

### Main execution graph

``` mermaid
flowchart TD
    U[User request] --> S[1. Supervisor]
    S --> P[2. Candidate Profile]
    P --> D[3. Discovery Planning]
    D --> M[4. Multi-Source Discovery]
    M --> R[5. Source Resolution and Deduplication]
    R --> F[6. Document Retrieval]
    F --> E[7. Opportunity Extraction]
    E --> V[8. Verification and Fraud Risk]
    V --> G{Safe and sufficiently supported?}
    G -->|No / uncertain| H[Human review queue]
    G -->|Yes / reviewable| EL[9. Eligibility Assessment]
    H --> EL
    EL --> RK[10. Ranking and Recommendation]
    RK --> AP[11. Application Preparation]
    AP --> HA[Human approval]
    HA -->|Approved| AT[12. Application Tracking]
    HA -->|Changes requested| AP
    AT --> S
```

The graph should support conditional branches. For example, a failed
fetch should go to a retry or retrieval-failure path, not to extraction
with empty content. A suspicious opportunity should be retained with
warnings and routed to review rather than silently discarded or
recommended as verified.

### Parallel execution

Parallelize independent tasks when their inputs are available:

-   Run government, academic/research, employer-career, and job-platform
    discovery adapters concurrently, subject to per-source rate limits.
-   Fetch independent vacancy URLs concurrently within a bounded
    concurrency limit.
-   Run deterministic metadata parsing and LLM semantic extraction in
    parallel on the same retrieved document.
-   Run independent employer-domain and vacancy-source corroboration
    checks in parallel.
-   Assess eligibility for separate opportunities concurrently after
    extraction and required verification gates.

Do not parallelize dependent decisions. Ranking must wait for the
relevant eligibility and verification results. Application preparation
must wait for a selected opportunity and a validated candidate profile.

### Coordination protocol

Every agent task should carry:

``` text
workflow_id
task_id
parent_task_id
agent_name
agent_version
input_schema_version
input_reference_ids
deadline
retry_count
privacy_classification
requested_output_schema
```

Every agent result should carry:

``` text
workflow_id
task_id
agent_name
agent_version
status
structured_output
evidence_reference_ids
warnings
confidence_or_uncertainty
tool_trace
model_provider
model_name
token_and_cost_metadata
started_at
completed_at
```

Use explicit status values such as:

-   `pending`
-   `running`
-   `succeeded`
-   `partial`
-   `needs_review`
-   `retryable_failure`
-   `terminal_failure`
-   `skipped`

Agents should return structured results, not unstructured prose as the
only communication mechanism.

------------------------------------------------------------------------

## 6. Shared state and memory design

Use a typed LangGraph state object. A conceptual state shape:

``` python
class NexoraWorkflowState(TypedDict):
    workflow_id: str
    user_request: str

    candidate_profile_ref: str | None
    discovery_plan: dict | None

    discovery_candidates: list[dict]
    resolved_opportunities: list[dict]
    retrieved_documents: list[dict]
    extracted_opportunities: list[dict]

    verification_reports: list[dict]
    eligibility_assessments: list[dict]
    rankings: list[dict]

    application_drafts: list[dict]
    application_events: list[dict]

    review_queue: list[dict]
    errors: list[dict]
    agent_runs: list[dict]

    workflow_status: str
    created_at: str
    updated_at: str
```

This is a conceptual contract, not a direction to copy this exact code
without adapting it to existing project schemas.

### Memory layers

  -----------------------------------------------------------------------
  Memory layer            Purpose                 Example
  ----------------------- ----------------------- -----------------------
  Agent working memory    Temporary task-specific Search terms already
                          notes                   tried in this run

  Workflow state          Shared state for one    Candidate records,
                          execution               documents, evidence,
                                                  decisions

  Persistent domain       Durable facts and       Candidate profile,
  memory                  history                 saved opportunities,
                                                  application status

  Source knowledge        Source-specific         Adapter configuration,
                          operational metadata    rate limits, last
                                                  successful check

  Evaluation memory       Test and quality data   Labeled extraction
                                                  examples,
                                                  false-positive reviews
  -----------------------------------------------------------------------

Do not store hidden chain-of-thought or unrestricted private reasoning.
Persist concise rationales, structured decisions, evidence references,
and audit metadata instead.

### Conflict resolution

When two agents disagree:

1.  Preserve both outputs and their provenance.
2.  Prefer deterministic source-backed parsing for explicitly labeled
    fields when its parser is validated for that source.
3.  Do not resolve semantic conflicts by arbitrary majority vote.
4.  Re-fetch or consult the original source when useful.
5.  Route unresolved high-impact conflicts to human review.
6.  Record the final resolution and why it was selected.

------------------------------------------------------------------------

## 7. Agent registry and configuration

Maintain a central registry describing every agent. Avoid scattering
model names, prompts, and tool permissions throughout the codebase.

Example conceptual configuration:

``` yaml
agents:
  supervisor:
    enabled: true
    model_profile: orchestration
    tools: [workflow_state, agent_registry, run_logger]

  candidate_profile:
    enabled: true
    model_profile: local_reasoning
    tools: [candidate_profile_store, profile_validator]

  discovery_planner:
    enabled: true
    model_profile: local_reasoning
    tools: [source_registry, query_builder]

  multi_source_discovery:
    enabled: true
    model_profile: local_reasoning
    tools: [ddgs_search, source_adapters]

  source_resolution:
    enabled: true
    model_profile: deterministic_first
    tools: [url_normalizer, redirect_resolver, deduplication_service]

  document_retrieval:
    enabled: true
    model_profile: deterministic_first
    tools: [safe_http_fetcher, permitted_browser, document_parser]

  opportunity_extraction:
    enabled: true
    model_profile: extraction
    tools: [metadata_parsers, structured_llm_extractor]

  verification_fraud:
    enabled: true
    model_profile: verification
    tools: [official_domain_lookup, search, url_analyzer, risk_rules]

  eligibility:
    enabled: true
    model_profile: deterministic_first
    tools: [eligibility_rules, candidate_profile_store]

  ranking:
    enabled: true
    model_profile: deterministic_first
    tools: [ranking_service]

  application_preparation:
    enabled: true
    model_profile: writing
    tools: [approved_candidate_documents, document_generator]

  application_tracking:
    enabled: true
    model_profile: deterministic_first
    tools: [application_store, scheduler, authorized_notifications]
```

The exact configuration format should follow the existing NEXORA
settings conventions. This example is illustrative; do not add
unsupported tools or dependencies simply to match it.

------------------------------------------------------------------------

## 8. Model routing and cost control

Do not run every agent through the most expensive model.

  -----------------------------------------------------------------------
  Task                    Preferred execution     Fallback
  ----------------------- ----------------------- -----------------------
  URL normalization and   Python deterministic    None needed
  deduplication           code                    

  Explicit metadata       Deterministic parsers   Local LLM for ambiguous
  extraction                                      layouts

  Semantic vacancy        Local Ollama model      Gemini if enabled and
  extraction                                      permitted

  Source verification     Search + deterministic  LLM summarizes evidence
  research                checks                  

  Eligibility rules       Deterministic rules     Human review for
                                                  ambiguity

  Ranking arithmetic      Deterministic scoring   LLM may explain, not
                                                  invent score

  Application drafting    Local model where       Gemini with user/data
                          adequate                permission

  Scheduling and status   Deterministic services  None needed
  updates                                         
  -----------------------------------------------------------------------

Implement: - Per-agent token and time budgets. - Per-workflow cost
ceilings. - Retry limits and exponential backoff where appropriate. -
Provider health checks and circuit breakers. - Caching for repeated
source retrieval and stable extraction. - Explicit policy before sending
candidate data to a cloud provider. - Structured logs of provider,
model, latency, and usage.

A model fallback should not silently change privacy policy.

------------------------------------------------------------------------

## 9. Human approval and safety gates

Human review is mandatory for high-impact or uncertain actions.

  -----------------------------------------------------------------------
  Action                              Automation policy
  ----------------------------------- -----------------------------------
  Discover public listings            Automatic within source rules

  Fetch permitted public pages        Automatic within retrieval
                                      safeguards

  Extract vacancy fields              Automatic with evidence validation

  Mark an employer/vacancy verified   Only after required corroboration;
                                      otherwise review

  Flag suspected fraud                Automatic risk flag with evidence;
                                      human review for consequential
                                      conclusions

  Assess eligibility                  Automatic preliminary assessment;
                                      review ambiguous cases

  Rank opportunities                  Automatic with explanation

  Draft application materials         Automatic draft; user reviews

  Send email or submit application    Explicit user approval required

  Change application status to        Require user confirmation or
  submitted                           trusted integration evidence
  -----------------------------------------------------------------------

No agent may bypass these gates through a tool call or indirect handoff.

------------------------------------------------------------------------

## 10. Failure handling and recovery

The orchestrator should implement bounded recovery paths.

  -----------------------------------------------------------------------
  Failure                             Expected behavior
  ----------------------------------- -----------------------------------
  Search provider unavailable         Retry within budget, then use
                                      another enabled source/provider

  One source adapter fails            Continue other sources and record
                                      partial coverage

  Duplicate uncertainty               Preserve candidates and route
                                      ambiguous matches to review

  Page fetch blocked                  Record access status; do not bypass
                                      restrictions

  PDF parsing fails                   Keep source URL and retrieval
                                      failure; try permitted alternative
                                      extraction if available

  LLM unavailable                     Use deterministic extraction where
                                      possible; mark semantic fields
                                      incomplete

  Invalid structured output           Validate, retry with bounded
                                      repair, then mark failed/review

  Evidence does not support field     Remove or mark unsupported; never
                                      silently retain it

  Verification sources conflict       Preserve conflict and request
                                      review

  Eligibility criteria ambiguous      `needs_review`, not automatic
                                      rejection

  Application integration unavailable Keep draft and checklist; do not
                                      claim submission
  -----------------------------------------------------------------------

Every failure should be observable and recoverable where safe. Do not
allow infinite agent loops.

------------------------------------------------------------------------

## 11. Evaluation: how to know each agent works

Each agent needs its own test suite and acceptance criteria. Evaluate
the full workflow separately.

  -----------------------------------------------------------------------
  Agent                               Example quality metrics
  ----------------------------------- -----------------------------------
  Supervisor                          Workflow completion rate, deadlock
                                      rate, retry correctness

  Candidate Profile                   Schema validity, provenance
                                      completeness, contradiction
                                      detection

  Discovery Planning                  Query relevance, constraint
                                      coverage

  Multi-Source Discovery              Unique relevant opportunities per
                                      source family, source diversity

  Source Resolution                   Duplicate precision/recall,
                                      canonical URL accuracy

  Document Retrieval                  Fetch success by source, extraction
                                      completeness, safe rejection
                                      accuracy

  Opportunity Extraction              Field precision/recall, evidence
                                      validity, null correctness

  Verification & Fraud Risk           Corroboration coverage,
                                      false-positive/false-negative rates
                                      on labeled cases

  Eligibility                         Criterion-level accuracy,
                                      false-eligible and false-ineligible
                                      rates

  Ranking                             Human-reviewed relevance, ranking
                                      stability, explanation fidelity

  Application Preparation             Factual consistency with candidate
                                      profile, user revision rate

  Application Tracking                Status integrity, reminder
                                      correctness, event-history
                                      completeness
  -----------------------------------------------------------------------

### Required test datasets

Maintain versioned test fixtures for:

-   Legitimate government and institutional vacancies.
-   Legitimate private-company vacancies.
-   Third-party listings that link to official employer pages.
-   Expired or closed vacancies.
-   Duplicate listings across multiple platforms.
-   Copied listings with changed contact details.
-   Fake employer and impersonation examples.
-   Listings with suspicious fees or misleading compensation.
-   Incomplete, login-gated, and dynamically rendered pages.
-   Conflicting duration, stipend, location, or eligibility statements.
-   Prompt-injection content embedded in pages and PDFs.

Use labeled examples and human-reviewed ground truth. Do not report a
fraud-detection accuracy figure until it has been measured on a
representative labeled dataset.

------------------------------------------------------------------------

## 12. Suggested implementation phases

Do not implement all 12 agents in one large change. Build the system in
stages, keeping each stage testable.

### Phase A --- Agent foundation

-   [ ] Define typed shared workflow state.
-   [ ] Define agent registry and versioned agent profiles.
-   [ ] Define common task/result envelopes and status values.
-   [ ] Add structured logging and agent-run tracing.
-   [ ] Add model routing, token budgets, timeouts, and retry policy.
-   [ ] Establish LangGraph orchestration and checkpointing.

**Acceptance:** Agents can be invoked through typed contracts, state is
inspectable, and failures are bounded.

### Phase B --- Discovery and source intelligence

-   [ ] Candidate Profile Agent.
-   [ ] Discovery Planning Agent.
-   [ ] Multi-Source Discovery Agent.
-   [ ] Modular source adapter registry.
-   [ ] Source Resolution & Deduplication Agent.

**Acceptance:** Multiple source families can produce normalized,
provenance-preserving candidates without one platform dominating the
workflow.

### Phase C --- Retrieval, extraction, and trust

-   [ ] Document Retrieval Agent.
-   [ ] Opportunity Extraction Agent.
-   [ ] Verification & Fraud-Risk Agent.
-   [ ] Evidence and conflict-resolution workflow.
-   [ ] Human review queue.

**Acceptance:** A vacancy record contains source provenance, structured
fields, field-level evidence, and separate verification/risk
assessments.

### Phase D --- Candidate intelligence

-   [ ] Eligibility Assessment Agent.
-   [ ] Ranking & Recommendation Agent.
-   [ ] Candidate profile versioning.
-   [ ] Evaluation datasets and metrics.

**Acceptance:** Each recommendation explains eligibility, relevance,
uncertainty, verification status, and ranking factors.

### Phase E --- Application lifecycle

-   [ ] Application Preparation Agent.
-   [ ] Application Tracking & Monitoring Agent.
-   [ ] User approval workflow.
-   [ ] Deadline and reminder services.
-   [ ] Dashboard integration.

**Acceptance:** A user can prepare, review, track, and update
applications without unauthorized submission.

### Phase F --- Production hardening

-   [ ] Persistent graph checkpoints and resumable workflows.
-   [ ] Role-based authorization for multi-user deployments.
-   [ ] Database migrations, backups, retention, and deletion.
-   [ ] Security testing for URL retrieval and untrusted documents.
-   [ ] Monitoring, alerting, load tests, and deployment automation.
-   [ ] Documented operational runbooks.

**Acceptance:** Production readiness is claimed only after measured
reliability, security, and operational criteria are met.

------------------------------------------------------------------------

## 13. Rules for adding more agents

Add a new agent only if all of the following are true:

1.  The responsibility is distinct from existing agents.
2.  It requires meaningful independent reasoning or policy.
3.  It has a well-defined input and output schema.
4.  It needs a distinct tool permission set or decision boundary.
5.  Its quality can be evaluated independently.
6.  The benefit outweighs additional latency, cost, state complexity,
    and debugging effort.

Examples of possible future agents: - **Deadline & Opportunity
Monitoring Agent:** only if ongoing monitoring becomes a substantial
independent workflow. - **Research Fit Agent:** if deep research-project
matching requires more than the current eligibility and ranking logic. -
**Application Quality Review Agent:** if application drafts need a
separate factual and requirement-compliance review. - **Source Health
Agent:** if adapter health, schema drift, and source reliability become
operationally complex.

These are optional future agents, not part of the initial 12-agent
target.

------------------------------------------------------------------------

## 14. Final architectural principles

1.  **Specialists, not a free-form swarm:** each agent has a narrow role
    and explicit contract.
2.  **Independent brains, shared facts:** separate instructions and
    working context, but one canonical source of truth.
3.  **Orchestrated coordination:** LangGraph controls execution,
    handoffs, parallel branches, retries, and review gates.
4.  **Deterministic before probabilistic:** use code for exact rules and
    calculations; use LLMs where semantic reasoning adds value.
5.  **Evidence before claims:** all important vacancy facts must be
    traceable to sources.
6.  **Trust is not inherited from a platform:** verify the individual
    employer, vacancy, and application destination.
7.  **Human control:** application submissions and external
    communications require explicit authorization.
8.  **Observable behavior:** every agent run, tool action, failure, and
    important decision must be auditable.
9.  **Cost-aware model routing:** use local models and deterministic
    services first where appropriate.
10. **Incremental implementation:** test each agent and each workflow
    stage before expanding the system.

## 15. Codex implementation instruction

Use this document as the target architecture for NEXORA's agentic AI
system.

Before coding:

1.  Audit the existing repository and identify current agents, services,
    schemas, workflow state, persistence, and tests.
2.  Map existing components to the 12 target agents. Reuse working
    components rather than duplicating them.
3.  Identify which responsibilities should remain deterministic services
    or source adapters instead of LLM agents.
4.  Present a phased migration plan with dependencies, files affected,
    risks, and acceptance tests.

Then implement Phase A first. Do not create all agents at once, do not
rewrite working modules unnecessarily, and do not claim an agent is
implemented until it has a defined contract, working integration, and
tests.

**Target outcome:** NEXORA should behave as one coordinated internship
intelligence system powered by specialist agents---not as a collection
of disconnected chatbots.
