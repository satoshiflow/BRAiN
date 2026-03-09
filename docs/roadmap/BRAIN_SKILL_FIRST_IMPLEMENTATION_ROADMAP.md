# BRAiN Final Layered Execution Roadmap

Version: 2.0
Status: Active Canonical Delivery Roadmap
Date: 2026-03-09
Purpose: Keep BRAiN Core slim and stable while evolving toward Experience, Insight,
Consolidation, Knowledge, and Evolution Control in incremental slices.

Companion roadmap:
- `docs/roadmap/BRAIN_MISSION_DELIBERATION_INSIGHT_ROADMAP.md`

Companion specifications:
- `docs/specs/observer_core_mvp.md`
- `docs/specs/discovery_observer_economy_sequencing.md`
- `docs/specs/discovery_layer_mvp.md`
- `docs/specs/economy_selection_support_mvp.md`

Execution status snapshot (2026-03-09):
- phases `P0` through `P7` are completed and verified in
  `docs/roadmap/IMPLEMENTATION_PROGRESS.md`.
- roadmap remains canonical for invariants, verification matrix, and
  post-P7 operating cadence.
- post-P7 recurring operation details are tracked in
  `docs/roadmap/BRAIN_POST_P7_OPERATIONS_CADENCE.md`.

---

## 1) Core Invariants (Hard Constraints)

1. `SkillRun` remains canonical execution truth.
2. Event backbone remains `EventStream` (ADR-001).
3. New runtime work lands in `backend/app/modules/*`.
4. No expansion of legacy `backend/modules/*` runtime writes.
5. Mutating paths require auth/role checks, audit durability, and lifecycle write guards.
6. API compatibility is preserved unless explicitly versioned and documented.
7. Every mutating contract declares an auth/role/scope matrix with deny-by-default behavior.
8. Tenant isolation is mandatory at write and read boundaries (`tenant_id` binding on write, enforced filters on read/list/search).
9. Ordering invariant for sensitive flows is durable state write -> durable audit record -> EventStream publish, with retry/outbox semantics.
10. Phase entry requires rollback plan, dual-write risk assessment, and security+migration approval.

---

## 2) Operating Model (Dev Agent Cluster)

Execution roles for each phase:
- `brain-orchestrator`: phase owner, gate decisions, sequencing.
- `brain-runtime-engineer`: module/runtime contract changes.
- `brain-schema-designer`: schema/event/error contracts.
- `brain-migration-engineer`: migrations, compatibility and rollback path.
- `brain-security-reviewer`: auth/tenant/audit review.
- `brain-verification-engineer`: test matrix, RC gate evidence.
- `brain-docs-scribe`: roadmap/spec synchronization.
- `brain-review-critic`: final critical review before merge.

Reviewer policy:
- Every phase closes with a strict externalized review pass (Claude-style critique
  checklist: governance, migration risk, tenant isolation, event/audit ordering,
  compatibility/deprecation, verification gates).

---

## 3) Phase Plan (P0-P7)

### Phase Entry/Exit Artifacts (Mandatory for Every Phase)

Entry artifacts:
1. contract diff (API/schema/events/errors).
2. migration plan (forward, backward, and rollback command path).
3. tenant isolation threat note for touched surfaces.
4. compatibility impact inventory (consumers, adapters, sunset assumptions).
5. endpoint-level auth/role/scope matrix for every mutating route in scope.
6. contract depth pack for new runtime objects: field model, validation rules,
   error codes, minimal API surface, event types, and durable-vs-ephemeral ownership.

Exit artifacts:
1. rollback rehearsal evidence.
2. deprecation ledger update.
3. RC gate evidence bundle.
4. reviewer sign-offs from security, migration, verification, and docs.
5. event/audit ordering conformance evidence for all new mutating surfaces.

### Phase P0 - Guardrails and Baseline Freeze

Goal:
- close remaining guardrail gaps before adding new learning artifacts.

#### Sprint P0.1 - Legacy Write Guard Closure
Tasks:
1. close lifecycle/decommission write-guard gaps on legacy edges (`api/routes/missions`, `app/modules/missions`, remaining mutating builder/ops routes).
2. add/extend tests proving `409` on `deprecated`/`retired` status.
3. record explicit write-owner transitions for touched routes.

#### Sprint P0.2 - Low-Risk Shim Reduction
Tasks:
1. remove only low-risk package/import side effects.
2. keep compatibility shims where import stability is uncertain.
3. validate repo-root and `backend/` test collection compatibility.

Stop/Go:
- Go if targeted tests + widened regression + RC gate pass.
- Stop if import/runtime stability regresses or new dual-write path appears.

---

### Phase P1 - Experience Layer MVP

Goal:
- introduce one minimal durable bridge object: `ExperienceRecord`.

#### Sprint P1.1 - Experience Contracts and Storage
Tasks:
1. add module `backend/app/modules/experience_layer/`.
2. add durable storage (`experience_records`) with idempotency keys.
3. define request/response/event contracts and sanitized error mapping.
4. define tenant ownership model for `ExperienceRecord` (writer identity, tenant binding, and cross-tenant rejection semantics).

#### Sprint P1.2 - Runtime Ingestion and Retrieval
Tasks:
1. implement `POST /api/experience/skill-runs/{run_id}/ingest`.
2. implement read endpoints by `experience_id` and `skill_run_id`.
3. enforce tenant-safe retrieval and lifecycle write guards.
4. add negative tests for cross-tenant read/write attempts and unauthorized breakglass paths.
5. define outbox/audit behavior for ingest partial failures (no orphan writes).
6. deliver endpoint auth/role/scope matrix for all experience endpoints.

Stop/Go:
- Go if `SkillRun` remains sole execution truth and experience writes are idempotent.
- Stop if phase scope expands to insight/pattern/evolution artifacts.

---

### Phase P1B - Observer Core MVP (Read-Only)

Goal:
- add a read-only observer side layer before Discovery to reduce integration risk.

#### Sprint P1B.1 - Observer Contracts and Storage
Tasks:
1. implement `backend/app/modules/observer_core/` with `ObservationSignal` and `ObserverState`.
2. define tenant-safe observer contracts and auth matrix for observer read endpoints.
3. enforce immutable signal ledger and idempotent ingestion keys.

#### Sprint P1B.2 - Observer Ingestion and Projection
Tasks:
1. consume read-only signals from `skill_engine`, `skill_evaluator`, `task_queue`, `runtime_auditor`, `system_health`, and `health_monitor`.
2. add EventStream consumer with replay-safe dedup behavior.
3. expose read APIs and operator-only replay/reconcile controls.
4. explicitly block any direct mutation path from observer to skills, workflows, and policies.

Stop/Go:
- Go if observer is fully read-only, tenant-safe, and does not alter execution outcomes.
- Stop if observer introduces control-path coupling or mutating side effects.

---

### Phase P2 - Insight and Knowledge Decoupling

Goal:
- derive bounded insight from experience and remove direct raw-run knowledge bypass.

#### Sprint P2.1 - Insight Layer Baseline
Tasks:
1. add `InsightCandidate` as first-class artifact with states (`proposed`, `provisional`, `validated`, `rejected`).
2. define required evidence links to `ExperienceRecord`.
3. add confidence/scope fields with deterministic validation rules.

#### Sprint P2.2 - Knowledge Input Normalization
Tasks:
1. re-route `knowledge_layer` ingest from direct `SkillRun` path to Experience/Insight mediation.
2. keep existing APIs stable using adapter path internally.
3. define deprecation contract for bypass paths (header/metadata, replacement endpoint, sunset date, migration owner).
4. set compatibility adapter SLO and rollback trigger if SLO is exceeded (`p95 latency <= 15% delta`, `5xx delta <= 0.5%`, `forced rollback if exceeded for 2 consecutive windows`).
5. add consumer-by-consumer cutover checklist with explicit exit gates.

Stop/Go:
- Go if existing clients are compatible and no direct raw execution to knowledge path remains active by default.
- Stop if migration requires breaking endpoint contracts in this phase.

---

### Phase P3 - Consolidation and Evolution Control MVP

Goal:
- add governed pattern formation and controlled evolution proposals.

#### Sprint P3.1 - Consolidation Layer
Tasks:
1. introduce `PatternCandidate` with recurrence/support/failure-mode fields.
2. add promotion preconditions and provenance guarantees.
3. persist `KnowledgePromotionRecord` for auditable promotion/rollback linkage.

#### Sprint P3.2 - Evolution Control Bootstrap
Tasks:
1. introduce `EvolutionProposal` lifecycle (`draft`, `review`, `approved`, `rejected`, `applied`, `rolled_back`).
2. bridge to existing `skills_registry` governance transitions.
3. require validation runs before proposal application.
4. define deterministic resolution/version invariants and ambiguity handling for proposal-to-skill activation.
5. enforce outbox-backed audit/event publication contract for proposal state transitions.

Stop/Go:
- Go if evolution remains policy-gated, reversible, and auditable.
- Stop if any unsupervised mutation path is introduced.

---

### Phase P4 - Deliberation and Tension Artifacts

Goal:
- add bounded mission-level deliberation artifacts without chain-of-thought storage.

#### Sprint P4.1 - Deliberation Summary
Tasks:
1. define `DeliberationSummary` (alternatives, rationale, uncertainty, open tensions).
2. link summaries to `ExperienceRecord` and mission context.
3. enforce data minimization and no raw hidden reasoning dumps.

#### Sprint P4.2 - Tension Modeling
Tasks:
1. define `MissionHypothesis`, `MissionPerspective`, `MissionTension` contracts.
2. allow unresolved tensions as valid outcomes.
3. add governance constraints for escalation/approval surfaces.
4. deliver endpoint auth/role/scope matrix for mutating deliberation endpoints.

Stop/Go:
- Go if artifacts remain bounded and non-invasive to execution path.
- Stop if deliberation artifacts alter canonical execution ownership.

---

### Phase P5 - Stabilization, Decommission, and Operational Cadence

Goal:
- lock the layered architecture and remove obsolete paths under governance.

#### Sprint P5.1 - Decommission Matrix Execution
Tasks:
1. execute staged retirement for deprecated direct-ingest and shadow runtime paths.
2. enforce kill-switch and replacement-target metadata.
3. execute decommission by ledger: consumer list, sunset approval, rollback command, and post-removal verification evidence.

#### Sprint P5.2 - Release Gate and Ongoing Cadence
Tasks:
1. run full verification matrix and RC gate.
2. publish release-ready architecture report (contracts, risk, rollback).
3. establish monthly roadmap/spec review cadence.
4. publish compatibility and deprecation closure report with consumer migration evidence.

Stop/Go:
- Go if all critical contracts are stable and RC gate remains green.
- Stop if any auth/audit/event ordering guarantee regresses.

---

### Phase P6 - Discovery Layer MVP (Proposal-Only)

Goal:
- introduce capability-gap detection and proposal generation after Knowledge and Observer baselines.

#### Sprint P6.1 - Discovery Contracts
Tasks:
1. implement `backend/app/modules/discovery_layer/` with `SkillGap`, `CapabilityGap`, `SkillProposal`, and `ProposalEvidence`.
2. define evidence thresholds sourced from Consolidation, Knowledge, and Observer signals.
3. enforce proposal-only behavior with no direct runtime mutation.

#### Sprint P6.2 - Evolution Control Handoff
Tasks:
1. integrate discovery output into governed review queues.
2. ensure all proposal promotion remains mediated by `evolution_control` and governance checks.
3. add de-dup and prioritization guards to prevent proposal inflation.

Stop/Go:
- Go if discovery proposals are reviewable, auditable, and mutation-free by design.
- Stop if discovery can bypass evolution control.

---

### Phase P7 - Economy and Selection Support

Goal:
- add minimal selection economics only after prior cognition layers are stable.

#### Sprint P7.1 - Economy Contract Baseline
Tasks:
1. define minimal scoring dimensions: confidence, frequency, impact, cost.
2. keep credits, karma/reputation, reward, and promotion-weight as distinct signals.
3. map where economy influences discovery prioritization and evolution review weighting.

#### Sprint P7.2 - Guarded Adoption
Tasks:
1. apply economy scoring only to prioritization, not direct mutation.
2. add anti-gaming and transparency rules for proposal ranking.
3. run controlled rollout with rollback-safe thresholds.

Stop/Go:
- Go if economy improves selection quality without reducing governance safety.
- Stop if economy collapses to opaque single-score control or reward hacking vectors.

---

## 4) Verification Matrix (Every Phase)

Mandatory checks:
1. targeted module tests and API contract tests for touched surfaces.
2. tenant isolation suite with cross-tenant negative tests for read/write/list/search paths.
3. migration suite: forward/backward rehearsal, replay/backfill checks, idempotency proof.
4. event/audit ordering tests under retry and broker failure scenarios.
5. `./scripts/run_rc_staging_gate.sh`.
6. quantitative gates: no Sev1 regressions, error-budget impact accepted, documented perf delta per phase.
7. evidence bundle: test artifacts, rollback evidence, deprecation ledger diff, reviewer approvals.

---

## 5) Non-Goals (Scope Guardrails)

1. No core rewrite of execution runtime.
2. No broad mission-runtime refactor in one phase.
3. No direct auto-promotion from raw runtime to evolution.
4. No multi-layer object rollout in the Experience MVP phase.
5. No deletion of compatibility paths without documented sunset criteria.
6. No direct mutation from Observer, Discovery, or Economy layers into active skill execution.

---

## 6) Done Criteria

Roadmap is done when:
1. Core remains slim: execution, orchestration, governance only.
2. Experience, Observer, Insight, Consolidation, Knowledge, Discovery, and Evolution Control exist as distinct governed layers.
3. `SkillRun` remains canonical execution anchor.
4. deprecated shadow paths are retired or adapter-bound under lifecycle governance.
5. economy/selection support is introduced only after layer contracts and governance gates are stable.
6. docs/specs/roadmaps are synchronized with verified runtime behavior.
