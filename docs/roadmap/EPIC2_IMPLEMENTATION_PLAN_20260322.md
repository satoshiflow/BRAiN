# Epic 2 Implementation Plan (2026-03-22)

## Goal

Converge BRAiN toward a single AXE-first communication surface while strengthening durable memory, governed self-learning, and controlled self-optimization loops.

## Baseline from Epic 1

- SkillRun state machine and transition events are in place.
- EvaluationResult is canonical; SkillRun evaluation summary remains projection.
- ProviderBinding persistence exists with governed status lifecycle.
- ProviderBinding router and health projection endpoints are available.
- AXE provider runtime now exposes governed binding context when available.

## Epic 2 Scope

1. AXE as communication frontdoor by default.
2. Memory split hardening (short-lived operational context vs durable knowledge).
3. Promotion/evolution pipeline from evaluated runs.
4. Safety-gated self-extension hooks (no uncontrolled runtime mutation).

## Work Phases

### Phase 1 - AXE Frontdoor Convergence

- Introduce a stable AXE intent contract for mission/skill invocation.
- Route AXE-triggered execution through SkillRun only.
- Add compatibility wrappers for legacy direct execution endpoints.
- Add deny/redirect logic for runtime-affecting paths that bypass SkillRun.

Done criteria:

- AXE requests can trigger SkillRuns directly with full provenance.
- No mission/agent path executes providers without SkillRun.

### Phase 2 - Memory Contract Hardening

- Define short-term memory contract (ephemeral context, Redis-backed where appropriate).
- Define long-term memory contract (Postgres-backed records and knowledge artifacts).
- Add explicit links: SkillRun -> EvaluationResult -> ExperienceRecord -> KnowledgeItem.
- Introduce retention and pruning rules for ephemeral layers.

Done criteria:

- Every completed SkillRun can be traced into durable knowledge through canonical references.

### Phase 3 - Governed Self-Learning Pipeline

- Add promotion candidate extraction from EvaluationResult + Experience.
- Add validation gates (reproducibility, policy compliance, risk thresholds).
- Add promotion decision model and event sequence.
- Introduce write paths for promoted assets (skills/prompts/routing hints) under governance.

Done criteria:

- No direct self-mutation without evaluation + validation + explicit promotion state.

### Phase 4 - Controlled Self-Optimization / Self-Extension

- Attach optimization proposals to governed queues (not direct apply).
- Require scope-limited rollout + rollback plan per proposal.
- Add audit and event coverage for all applied optimization actions.
- Add kill-switches for autonomous adaptation loops.

Done criteria:

- BRAiN can propose and apply improvements only through governed, reversible control-plane flows.

### Phase 5 - Runtime and Operations Hardening

- Expand Redis availability projections for provider and execution health.
- Add operational dashboards/read models for run/eval/promotion health.
- Add incident playbooks for provider quarantine and learning rollback.

Done criteria:

- Operators can observe, pause, and rollback adaptive behavior from AXE/control plane.

## Mandatory Invariants for Epic 2

- SkillRun remains the only execution truth.
- Mission never becomes runtime.
- AXE remains frontdoor, not governance source of truth.
- Postgres remains canonical; Redis remains ephemeral.
- Learning and optimization paths remain policy-gated and auditable.

## Verification Strategy

- Targeted tests per phase + local CI gate (`backend-fast`) each slice.
- RC gate before merge-candidate milestones.
- Evidence logs in `docs/roadmap/local_ci/` for each delivery slice.

## Risks to Track

- AXE convenience flows reintroducing provider-level bypasses.
- Over-eager auto-learning creating low-quality promotions.
- Ephemeral memory leaking into canonical truth without validation.
- Legacy routes becoming shadow runtimes.
