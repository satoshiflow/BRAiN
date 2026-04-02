# BRAiN Context/Session Execution Brief (Dev Agent)

Status: Ready for implementation
Source: `docs/specs/BRAIN_CONTEXT_SESSION_READINESS_PLAN_20260401.md`

## Mission

Implement token-aware, governed context/session handling for AXE/BRAiN so long sessions remain stable, auditable, and cost-controlled.

## Constraints (non-negotiable)

- Do not introduce a second runtime authority.
- `SkillRun` remains canonical execution anchor.
- Governance context must never be dropped by context trimming.
- No raw chain-of-thought persistence.
- Keep tenant boundaries intact in all context/memory retrieval paths.

## Current baseline (must be preserved)

- AXE request limits exist in `backend/app/modules/axe_fusion/router.py`
  - `MAX_MESSAGE_LENGTH = 10000`
  - `MAX_MESSAGES_PER_REQUEST = 100`
- Session/message persistence exists in `backend/app/modules/axe_sessions/models.py`
- Worker and activity UX surfaces already exist in AXE chat.

## Deliver in 6 slices

## Slice 1 - Token estimation + telemetry

Goal:
- Add request-time token estimation and prompt-budget telemetry.

Implement:
- Context token estimate before provider call.
- Record fields: `estimated_prompt_tokens`, `context_mode`, `trim_applied`, `trim_reason`.
- Surface minimal telemetry to AXE UI (read-only display).

Tests:
- unit tests for estimator and budget thresholds.
- integration test proving telemetry fields are present.

Done when:
- every AXE chat request has token estimate + context mode metadata.

## Slice 2 - Context envelope + tiering

Goal:
- Replace flat history replay with explicit envelope segments.

Implement segments:
- governance/system
- active turn
- short-term turns
- retrieved knowledge/memory
- optional worker/runtime evidence

Tests:
- segment ordering and inclusion tests.
- guard tests: governance segment always included.

Done when:
- prompt assembly is deterministic and segment-based.

## Slice 3 - Session compression summaries

Goal:
- Introduce structured summary artifacts for long sessions.

Implement:
- trigger thresholds for summary creation.
- summary artifact with provenance fields.
- use summary in context envelope when threshold crossed.

Tests:
- summary generation trigger tests.
- summary reuse tests.

Done when:
- long sessions no longer require large raw replay to stay coherent.

## Slice 4 - Relevance-scored retrieval

Goal:
- Use relevance selection instead of broad history replay.

Implement:
- scoring inputs: intent overlap, domain, unresolved tasks, artifact refs.
- top-K retrieval policy with deterministic fallback.

Tests:
- scoring correctness tests.
- deterministic tie-break behavior.

Done when:
- only relevant context slices are included in large-session turns.

## Slice 5 - AXE transparency indicators

Goal:
- Make context decisions operator-visible.

Implement:
- show `context_mode` (`full`, `compacted`, `retrieval_augmented`).
- show token class (`small`, `medium`, `large`).
- show "compaction applied" hint when relevant.

Tests:
- UI tests for all indicator states.

Done when:
- operators can see how BRAiN built context for each response.

## Slice 6 - Soak + acceptance evidence

Goal:
- prove production behavior under long-running/parallel conditions.

Run profiles:
1. long session (100+ turns)
2. attachment-heavy session
3. mixed worker activity (`miniworker`, `opencode`, `openclaw`)

Capture metrics:
- success rate
- p50/p95 latency
- token estimate distribution
- compaction rate
- failure categories

Done when:
- evidence is written and acceptance criteria pass.

## Acceptance criteria

- No oversize failures in target soak profiles.
- Stable response quality in long sessions.
- Context trimming decisions auditable.
- Governance hints and approval/risk constraints preserved.
- Token/cost behavior remains within policy thresholds.

## Output expected from Dev Agent

For each slice provide:
- changed files
- contract/schema deltas
- test commands + results
- known risks
- rollback strategy

At end provide:
- final evidence references
- "ready/not-ready" verdict with rationale
