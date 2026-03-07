# BRAIN Architecture Implementation Report

Date: 2026-03-06
Scope: First architectural stabilization layer

## Modules created

### 1) Immune Orchestrator

Path: `backend/app/modules/immune_orchestrator`

Created files:
- `schemas.py`
- `priority_engine.py`
- `playbook_registry.py`
- `service.py`
- `router.py`

Core capabilities:
- incident signal intake (`IncidentSignal`)
- severity/blast-radius/confidence/recurrence priority scoring
- playbook action decision: `observe|warn|mitigate|isolate|escalate`
- mandatory decision event emission: `immune.decision`
- mandatory audit entry creation for every decision
- module metrics endpoint model

### 2) Unified Recovery Policy Engine

Path: `backend/app/modules/recovery_policy_engine`

Created files:
- `schemas.py`
- `policy_engine.py`
- `service.py`
- `router.py`
- `adapters/__init__.py`
- `adapters/planning_adapter.py`
- `adapters/neurorail_adapter.py`
- `adapters/task_queue_adapter.py`

Core capabilities:
- centralized recovery decisioning
- supported strategies:
  - `retry`
  - `circuit_break`
  - `rollback`
  - `backpressure`
  - `detox`
  - `isolate`
  - `escalate`
- policy configuration support:
  - `max_retries`
  - `cooldown_seconds`
  - `escalation_threshold`
  - `allowed_actions`
- mandatory decision event emission: `recovery.action`
- mandatory audit entry creation for every recovery decision
- adapter bridge for planning/neurorail/task_queue

### 3) Genetic Integrity Service

Path: `backend/app/modules/genetic_integrity`

Created files:
- `schemas.py`
- `hashing.py`
- `verification.py`
- `service.py`
- `router.py`

Core capabilities:
- canonical DNA payload serialization
- snapshot hash generation over:
  - `agent_id`
  - `snapshot_version`
  - `parent_snapshot`
  - `dna_payload`
- parent snapshot linking via parent hash reference
- mutation audit trail with governance hook flag
- events:
  - `genetic_integrity.snapshot_registered`
  - `genetic_integrity.mutation_recorded`
- module metrics endpoint model

## APIs exposed

### Immune Orchestrator API
- `POST /api/immune-orchestrator/signals`
- `GET /api/immune-orchestrator/signals`
- `GET /api/immune-orchestrator/decisions`
- `GET /api/immune-orchestrator/audit`
- `GET /api/immune-orchestrator/metrics`

### Recovery Policy Engine API
- `POST /api/recovery-policy/decide`
- `POST /api/recovery-policy/decide/{adapter_name}`
- `GET /api/recovery-policy/policy`
- `PUT /api/recovery-policy/policy`
- `GET /api/recovery-policy/decisions`
- `GET /api/recovery-policy/audit`
- `GET /api/recovery-policy/metrics`

### Genetic Integrity API
- `POST /api/genetic-integrity/snapshots/register`
- `GET /api/genetic-integrity/snapshots`
- `GET /api/genetic-integrity/snapshots/{agent_id}/{snapshot_version}`
- `POST /api/genetic-integrity/snapshots/{agent_id}/{snapshot_version}/verify`
- `POST /api/genetic-integrity/mutations/record`
- `GET /api/genetic-integrity/mutations`
- `GET /api/genetic-integrity/audit`
- `GET /api/genetic-integrity/metrics`

## Integration points

### Runtime integration
- `backend/main.py` updated:
  - imports and router registration for all three modules
  - EventStream wiring into module services during startup

### DNA/Genesis integration
- `backend/app/modules/dna/router.py` updated (additive):
  - after snapshot creation: register genetic integrity snapshot
  - after mutation: register snapshot + mutation audit trail
  - best-effort wrapping to avoid breaking existing DNA API behavior

## Test scaffolding added

Path: `backend/tests/modules/`

Files:
- `test_immune_orchestrator.py`
- `test_recovery_policy_engine.py`
- `test_genetic_integrity.py`

Coverage intent:
- unit-level decision logic
- adapter path sanity
- hash/verify consistency
- audit/metrics increment behavior

## Migration risks

1. Existing EventStream usage is heterogeneous across modules.
   - Risk: payload schema variance across current publishers.
2. New services are in-memory at this stage.
   - Risk: decision/audit state not durable across restarts.
3. DNA integration is additive in router path only.
   - Risk: alternate DNA mutation paths may bypass integrity service until full service-level migration.
4. Governance hooks are present as flags, not full workflow enforcement.
   - Risk: high-risk actions still depend on external governance integration completion.

## Future improvements

1. Persist orchestrator/recovery/integrity audit stores in PostgreSQL.
2. Standardize runtime event envelope and severity taxonomy across all publishers.
3. Move genetic integrity registration from router-level hook to DNA service core path.
4. Add full governance approval flow for:
   - isolate/escalate recovery decisions
   - high-risk DNA mutations
5. Add OpenCode Dev/Repair ticket handoff from immune/recovery decisions.

## Stabilization Block 2 (production hardening)

### 1) Persistence changes

Primary persistence path added for all three modules with DB-first behavior and in-memory fallback:

- Immune Orchestrator
  - `backend/app/modules/immune_orchestrator/models.py`
  - persisted entities:
    - `immune_orchestrator_signals`
    - `immune_orchestrator_decisions`
    - `immune_orchestrator_audit`

- Recovery Policy Engine
  - `backend/app/modules/recovery_policy_engine/models.py`
  - persisted entities:
    - `recovery_policy_requests`
    - `recovery_policy_decisions`
    - `recovery_policy_audit`

- Genetic Integrity
  - `backend/app/modules/genetic_integrity/models.py`
  - persisted entities:
    - `genetic_integrity_snapshots`
    - `genetic_integrity_mutations`
    - `genetic_integrity_audit`

Notes:
- services now accept `db: AsyncSession | None` and use DB session when available
- router endpoints for all 3 modules now pass `get_db` sessions
- if DB persistence fails (missing tables/migration drift), services degrade to in-memory state

Migration note (important):
- Table models are added and used as primary path.
- Alembic migration added:
  - `backend/alembic/versions/017_add_stabilization_layer_persistence.py`

### 2) Unified audit path

Implemented central audit bridge:

- `backend/app/core/audit_bridge.py`

All three modules now write unified audit events through existing audit logging architecture (`audit_events`) including:
- `correlation_id`
- module-specific identifiers (`decision_id`, `incident_id`, `mutation_id`)

Audit bugfix applied:
- `backend/app/modules/audit_logging/service.py`
  - fixed payload field mapping to `extra_data`.

### 3) Standardized event schema

Implemented reusable event contract:

- `backend/app/core/event_contract.py`

Standardized envelope fields:
- `event_type`
- `severity`
- `source`
- `entity`
- `correlation_id`
- `occurred_at`
- `data`

Applied to:
- `immune.decision`
- `recovery.action`
- `genetic_integrity.snapshot_registered`
- `genetic_integrity.mutation_recorded`

Contract tests added:
- `backend/tests/modules/test_arch_event_contracts.py`

### 4) Deeper recovery adapter integration

Recovery engine integration hookpoints were added into core runtime components:

- Planning recovery path:
  - `backend/app/modules/planning/failure_recovery.py`
  - central policy consulted before strategy execution (adapter `planning`)

- Task queue failure path:
  - `backend/app/modules/task_queue/service.py`
  - central policy consulted in `fail_task` (adapter `task_queue`)

- NeuroRail retry path:
  - `backend/app/modules/neurorail/enforcement/retry.py`
  - central policy consulted on retry failures (adapter `neurorail`)

Compatibility:
- existing local logic remains as fallback; no breaking API change.

### 5) Deeper DNA/Genesis integration

Moved integrity integration into DNA core path (service-level, not only router-level):

- `backend/app/modules/dna/core/service.py`
  - automatic snapshot registration in genetic integrity on create/mutate
  - automatic mutation audit trail on mutate
  - governance check hook prepared (`set_mutation_governance_hook`) for high-risk mutation gating

- `backend/app/modules/dna/router.py`
  - simplified back to API wrapper; core integration now handled inside DNA service

- `backend/app/modules/genesis/core/service.py`
  - DNA service used by Genesis now wired to genetic integrity service
  - fixed async mutation call path (`await self.dna.mutate(...)`)

### 6) RC / staging verification gate preparation

Added staging gate artifacts:

- checklist:
  - `docs/architecture/RC_STAGING_VERIFICATION_CHECKLIST.md`

- executable gate script:
  - `scripts/run_rc_staging_gate.sh`

Verification focus areas in gate:
- auth + agent lifecycle
- incident -> immune decision
- recovery action flow
- DNA mutation -> integrity + audit
- architecture guardrails

### Tests executed in this block

Green:
- `PYTHONPATH=. pytest tests/modules/test_immune_orchestrator.py tests/modules/test_recovery_policy_engine.py tests/modules/test_genetic_integrity.py tests/modules/test_arch_event_contracts.py -q`
- `PYTHONPATH=. pytest tests/test_dna_events.py tests/test_auth_flow.py tests/test_module_auth.py tests/test_paycore_ownership.py -q`

Additional verification (follow-up):
- `python3 -m py_compile backend/alembic/versions/017_add_stabilization_layer_persistence.py backend/app/modules/genetic_integrity/service.py`
- `PYTHONPATH=. pytest tests/modules/test_immune_orchestrator.py tests/modules/test_recovery_policy_engine.py tests/modules/test_genetic_integrity.py tests/modules/test_arch_event_contracts.py -q`
- `./scripts/run_rc_staging_gate.sh` still fails on known pre-existing `tests/test_supervisor_agent.py` policy model issue.

Known pre-existing failures (outside this change scope):
- `tests/test_reflex_actions.py` currently blocked by existing syntax issue in `neurorail/reflex/triggers.py`
- `tests/test_supervisor_agent.py` currently blocked by existing policy model reserved-name issue (`metadata`) in `app/models/policy.py`

### Remaining risks

1. DB tables for new persistence models require migration rollout; fallback mode masks missing schema in dev.
2. Existing legacy/runtime paths still coexist and can bypass central recovery decisions in edge flows.
3. Some broader test suites have unrelated pre-existing blockers; full RC gate requires those baseline issues resolved.
4. DNA module still carries `datetime.utcnow()` deprecation warnings in non-auth scope.

### Recommended next step

Proceed with **Genetic Quarantine Manager** on top of this hardened foundation, then integrate **OpenCode Dev/Repair ticket handoff** using:
- immune decision outputs
- recovery decisions
- genetic mutation governance hooks.
