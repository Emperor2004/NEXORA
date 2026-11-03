# Modular architecture

This document describes the current module boundaries and the direction for
future changes. Keep orchestration at the edges and business logic in focused
modules with explicit inputs and outputs.

## Backend

- `app/main.py` owns FastAPI construction, middleware, and route wiring.
- `app/agents/` contains agent behavior and the registered agent catalog.
- `app/graph/` owns typed workflow state and graph orchestration.
- `app/schemas/` owns request, response, and agent contracts.
- `app/services/` contains single-purpose domain and integration services.
- `workflow_planner.py` builds the discovery plan and source-targeted queries.
- `workflow_source_resolver.py` resolves search results and LinkedIn listing
  pages to original vacancy URLs.
- `workflow_document_processor.py` retrieves, extracts, verifies, assesses,
  ranks, deduplicates, and persists one vacancy record per call.
- `workflow_matching.py` contains deterministic identity and listing-match
  helpers.
- `workflow_result_builder.py` performs cross-result corroboration and shapes
  the workflow response.
- `internship_workflow_service.py` remains the stable workflow facade used by
  API and graph callers; it coordinates those modules.

## Frontend

- `src/lib/` contains API transport and shared request logic.
- `src/ui/components/` contains reusable domain components and query hooks.
- `src/ui/pages/` contains one page module per user-facing workflow area.
- `src/ui/App.tsx` owns route composition, the shared shell, and top-level
  query/mutation wiring.
- `src/types.ts` defines shared API response types.

## Change rules

1. Keep external API routes and request/response shapes stable unless a
   deliberate API change is part of the task.
2. Put deterministic transformations in pure helpers where practical.
3. Keep I/O behind existing service interfaces; do not mix UI rendering,
   network access, database writes, and workflow policy in one module.
4. Preserve source provenance and field evidence through every module boundary.
5. Add focused regression coverage when a module contract or workflow behavior
   changes.
