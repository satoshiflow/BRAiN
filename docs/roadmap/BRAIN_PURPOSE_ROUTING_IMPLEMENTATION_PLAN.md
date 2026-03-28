# BRAiN Purpose/Routing Implementation Plan (Small Tasks)

Status: In progress. Backend core (Phases A-D, F) implemented; UI/control
surfaces (Phase E) remain pending.

## Goal

Implement canonical identity/purpose/routing integration in existing BRAiN
architecture with `brain_first` default autonomy, no parallel runtime, and
sandbox-first evolution controls.

## Global Rules

- Reuse existing modules and contracts first.
- Keep `SkillRun` as canonical execution record.
- Keep `domain_agents` as upper routing/review spine.
- Keep lower provider routing in `provider_bindings` and capability runtime.
- Keep learning/evolution attached to
  `experience -> insight -> consolidation/pattern -> evolution`.
- Route human controls through AXE, with policy-defined required approvals only.

## Phase A - Contract and spec lock

### Sprint A1 - Canonical docs lock

- [x] A1.1 Confirm source precedence in `DESIGN.md`, `AGENTS.md`, and
      governance specs.
- [x] A1.2 Mark non-canonical/outdated sources as informational where needed.
- [x] A1.3 Validate no terminology conflicts across new contract specs.

### Sprint A2 - Contract schema lock

- [x] A2.1 Finalize `canonical_identity_contract.md` field model.
- [x] A2.2 Finalize `purpose_profile_contract.md` field model.
- [x] A2.3 Finalize `purpose_evaluation_contract.md` field model.
- [x] A2.4 Finalize `purpose_routing_attachment_contract.md` ownership and
      invariants.

### Sprint A3 - Acceptance criteria lock

- [x] A3.1 Define testable acceptance checks for each new contract.
- [x] A3.2 Define governance-required vs optional human review matrix.
- [x] A3.3 Define event/audit minimums for purpose/routing decisions.

## Phase B - Backend contract introduction (non-breaking)

### Sprint B1 - Shared schemas

- [x] B1.1 Add `DecisionContext` schema in existing upper orchestration surface
      (domain-agent-adjacent module).
- [x] B1.2 Add `PurposeEvaluation` schema with outcomes
      `accept/reject/modified_accept`.
- [x] B1.3 Add `TaskProfile` schema.
- [x] B1.4 Add `WorkerProfileProjection` schema.
- [x] B1.5 Add `RoutingDecision` schema.

### Sprint B2 - Persistence models (minimal)

- [x] B2.1 Add durable model for `PurposeEvaluation` records.
- [x] B2.2 Add durable model for `RoutingDecision` records.
- [x] B2.3 Add linkage fields to preserve mission/tenant/correlation continuity.
- [x] B2.4 Add migration scripts for new tables/fields.

### Sprint B3 - API surfaces (internal-safe)

- [x] B3.1 Add read/write endpoints for purpose evaluation artifacts.
- [x] B3.2 Add read endpoints for routing decision artifacts.
- [x] B3.3 Enforce auth/role checks and tenant derivation rules.
- [x] B3.4 Emit control-plane events and audit records for sensitive writes.

## Phase C - Runtime integration (no bypass)

### Sprint C1 - Upper flow wiring

- [x] C1.1 Normalize ingress intent to `DecisionContext`.
- [x] C1.2 Run purpose evaluation before domain resolution.
- [x] C1.3 Generate task profile before routing choice.
- [x] C1.4 Produce and persist routing decision before `SkillRun` creation.

### Sprint C2 - Domain and execution handoff

- [x] C2.1 Attach context/evaluation into `domain_agents` service flow.
- [x] C2.2 Attach routing decision snapshot into `SkillRun` creation flow.
- [x] C2.3 Preserve approval waits for high/critical risk tiers.
- [x] C2.4 Verify no execution path bypasses `SkillRun`.

### Sprint C3 - Lower-layer isolation

- [x] C3.1 Ensure provider selection still uses `provider_bindings`.
- [x] C3.2 Ensure task dispatch stays subordinate to `SkillRun`.
- [x] C3.3 Ensure OpenCode contracts remain bounded execution artifacts.

## Phase D - Learning and evolution integration

### Sprint D1 - Routing memory projection

- [x] D1.1 Define routing-memory projection fields from existing evaluation and
      experience outputs.
- [x] D1.2 Persist or materialize projection without creating a new learning
      subsystem.
- [x] D1.3 Expose read endpoint for routing-memory insights.

### Sprint D2 - Replay and tuning foundations

- [x] D2.1 Add replay-friendly comparison utility for routing outcomes.
- [x] D2.2 Add baseline metrics: success, cost, latency, sovereignty fit.
- [x] D2.3 Add non-production tuning hooks only.

## Phase E - AXE and ControlDeck surfaces

Execution detail for this phase is tracked in:
- `docs/roadmap/BRAIN_PURPOSE_ROUTING_PHASE_E_UI_TASKS.md`

### Sprint E1 - Visibility first

- [ ] E1.1 Add AXE view for purpose/routing explanation traces. (Pending UI)
- [ ] E1.2 Add ControlDeck views for governed-editable profiles/policies. (Pending UI)
- [ ] E1.3 Add read-only views for decision artifacts and routing memory. (Pending UI)

### Sprint E2 - Governed controls

- [ ] E2.1 Add controlled edit workflows for `PurposeProfile` and
      `RoutingPolicy`.
- [ ] E2.2 Add override workflow in AXE with mandatory audit trail.
- [ ] E2.3 Add simulation/sandbox run controls before production activation.

## Phase F - Verification, hardening, and rollout

### Sprint F1 - Backend tests

- [x] F1.1 Unit tests for purpose evaluation outcomes and validation.
- [x] F1.2 Unit tests for routing decision constraints and tie-break behavior.
- [x] F1.3 Integration tests for
      `mission -> domain -> routing -> skillrun` flow.
- [x] F1.4 Integration tests for approval-required sensitive paths.

### Sprint F2 - Governance and traceability checks

- [x] F2.1 Verify tenant/correlation/causation continuity end-to-end.
- [x] F2.2 Verify audit/event emission for sensitive transitions.
- [x] F2.3 Verify immutable execution ownership by `SkillRun`.

### Sprint F3 - Local gates and rollout evidence

- [x] F3.1 Run targeted pytest suites for touched modules.
- [x] F3.2 Run `./scripts/run_rc_staging_gate.sh`.
- [x] F3.3 Record validation evidence in roadmap/local CI notes.
- [x] F3.4 Define rollback strategy before production promotion.

### Rollback strategy (defined)

- Keep migrations reversible via Alembic downgrades:
  - `044_add_purpose_and_routing_decisions`
  - `045_add_routing_memory_and_adaptation`
- Keep runtime fallback path by bypassing new endpoints and using existing
  `domain_agents -> skill_engine` create/execute flows.
- Disable adaptation behavior by default outside sandbox (`BRAIN_SANDBOX_MODE`
  off) and through evolution adaptive freeze controls.
- If governance anomalies occur, set adaptive freeze and block routing
  adaptation transitions to `approved`/`applied`.

## Parallel workstreams map

- WS1 Contracts/docs: Phase A
- WS2 Purpose contracts: Phase B1/B2
- WS3 Routing core: Phase B1/C1
- WS4 Governance integration: Phase B3/C2
- WS5 Execution bridge: Phase C
- WS6 Learning integration: Phase D
- WS7 UI/control surfaces: Phase E
- WS8 Verification/hardening: Phase F

## Hard checkpoints

- CP1 Contract lock complete (Phase A done)
- CP2 Purpose and routing artifacts persisted (Phase B done)
- CP3 Canonical handoff to SkillRun verified (Phase C done)
- CP4 Learning projection integrated (Phase D done)
- CP5 AXE/ControlDeck operational surfaces available (Phase E done)
- CP6 Tests + RC gate + rollout evidence complete (Phase F done)
