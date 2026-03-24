# Observer Core MVP Specification (Read-Only)

Status: Draft (implementation-ready outline)  
Scope: Read-only observability core for BRAiN runtime state and signals.

## 1) Purpose

Observer Core MVP provides a tenant-scoped, read-only runtime view that:
- consolidates signals from existing BRAiN modules into one normalized `ObservationSignal` stream,
- maintains a queryable `ObserverState` snapshot per tenant,
- exposes read APIs for operators, viewers, and service principals,
- publishes observer lifecycle events and audit records without mutating source modules.

Primary value in MVP:
- consistent runtime awareness across `skill_engine`, `skill_evaluator`, `learning`, `runtime_auditor`, `health_monitor`, `system_health`, `task_queue`, `telemetry`, `audit_logging`, `immune_orchestrator`, and `recovery_policy_engine`;
- deterministic event-to-snapshot behavior with idempotent ingestion;
- governance-safe foundation for later Discovery Layer consumption.

## 2) Explicit Non-Goals (MVP)

- No autonomous action, remediation, policy mutation, or queue mutation.
- No write endpoint for external clients (except internal ingestion adapters).
- No cross-tenant analytics joins in default read APIs.
- No ranking/recommendation engine in Observer Core itself.
- No replacement of source module ownership (source modules remain system-of-record for their domains).
- Discovery Layer implementation is deferred; only a future consumer of Observer signals.

## 3) Architecture Placement

### 3.1 New module

- Add new module: `backend/app/modules/observer_core/`
  - `models.py` (durable state + signal ledger)
  - `schemas.py` (API + ingestion contracts)
  - `service.py` (normalization, idempotency, snapshot updates)
  - `router.py` (read-only API)
  - `adapters/` (module-specific mappers)

### 3.2 Position in runtime layering

- Observer Core sits beside existing app modules as an observability consolidation layer.
- Event backbone remains `mission_control_core/core/event_stream.py`.
- Existing modules keep producing domain events/states; Observer Core only ingests and projects.
- Discovery Layer remains a next-phase consumer and is not part of this implementation.

## 4) Object Model

### 4.1 `ObservationSignal` (immutable, append-only)

Canonical normalized signal envelope:
- `signal_id` (UUID)
- `tenant_id` (required)
- `source_module` (enum-like string; e.g. `skill_engine`, `runtime_auditor`)
- `source_event_type` (string)
- `source_event_id` (optional string)
- `correlation_id` (optional string)
- `entity_type` (e.g. `skill_run`, `task`, `service`, `system`)
- `entity_id` (string)
- `signal_class` (`state_change | health | performance | risk | audit_ref | lifecycle`)
- `severity` (`info | warning | critical`)
- `occurred_at` (source time)
- `ingested_at` (observer time)
- `payload` (normalized bounded JSON)
- `payload_hash` (sha256 for idempotency/verifiability)
- `ordering_key` (per-entity monotonic sequence marker when available)

Rules:
- Immutable after insert.
- Per-tenant query isolation.
- Source payload redaction/anonymization inherited from source module contracts.

### 4.2 `ObserverState` (latest snapshot per tenant + scope)

Snapshot projection object:
- `observer_state_id` (UUID)
- `tenant_id`
- `scope_type` (`tenant_global | entity`)
- `scope_entity_type` (nullable)
- `scope_entity_id` (nullable)
- `snapshot_version` (monotonic int per scope)
- `last_signal_id`
- `last_occurred_at`
- `health_summary` (JSON)
- `risk_summary` (JSON)
- `execution_summary` (JSON)
- `queue_summary` (JSON)
- `audit_refs` (array of IDs/links)
- `snapshot_payload` (bounded JSON)
- `created_at`, `updated_at`

Rules:
- Derived only from `ObservationSignal` records.
- Upsert per `(tenant_id, scope_type, scope_entity_type, scope_entity_id)`.
- Monotonic `snapshot_version`; never decrement.

## 5) Integration Points (existing modules)

Observer adapters consume existing module outputs without changing source ownership:

- `skill_engine`: `SkillRun` lifecycle and state transitions -> execution/lifecycle signals.
- `skill_evaluator`: evaluation completion/compliance -> quality/risk signals.
- `learning`: metric/strategy/experiment events -> adaptation signals (read-only ingestion).
- `runtime_auditor`: anomalies/edge-of-chaos -> health/performance/risk signals.
- `health_monitor`: service check outcomes -> service-health signals.
- `system_health`: aggregate status summaries -> tenant-global health signals.
- `task_queue`: queue depth, task state transitions, lease lifecycle -> queue/execution signals.
- `telemetry`: runtime telemetry events (bounded) -> performance signals.
- `audit_logging`: audit events -> audit_ref signals (not duplicating full audit records).
- `immune_orchestrator`: incident and decision events -> risk/governance signals.
- `recovery_policy_engine`: recovery requests/actions -> risk/lifecycle signals.

Adapter contract:
- map source event -> normalized `ObservationSignal`;
- enforce tenant derivation rules;
- reject malformed/untenantable events to dead-letter stream with audit marker.

## 6) Event Ingestion + Snapshot Polling

### 6.1 Ingestion modes

- Event push ingestion (primary): subscribe to `EventStream` runtime events.
- Snapshot polling (supporting): scheduled pull from source read APIs for drift correction and cold-start backfill.

### 6.2 Polling targets (MVP)

- `system_health` summary endpoints.
- `health_monitor` status/history summaries.
- `task_queue` queue stats.
- `skill_engine` recent runs + state.
- `skill_evaluator` recent evaluations.

### 6.3 Reconciliation model

- Event ingestion is near-real-time path.
- Polling is anti-entropy path (e.g., every 60s-300s configurable).
- Polling emits synthetic `ObservationSignal` with `source_event_type=<module>.snapshot_polled.v1`.
- Snapshot writes must remain idempotent and version-monotonic.

## 7) Tenant Isolation Model

- Every `ObservationSignal` must resolve a `tenant_id` at ingest time.
- Signals without tenant are rejected by default (except explicitly `system` tenant where contract permits).
- Read APIs always filter by principal tenant unless admin role.
- Cross-tenant aggregation endpoints are not exposed in MVP.
- DB constraints/indexes include `tenant_id` as leading key on all observer tables.

## 8) Auth and Role Matrix

Use existing auth dependencies (`require_auth`, `require_role`, optional `require_scope`):

| Endpoint class | Roles | Scopes | Notes |
|---|---|---|---|
| Read signals/snapshots | `viewer`, `operator`, `admin`, `service` | `read` or `system:read` | Tenant-bound by principal |
| Read tenant health summary | `viewer`, `operator`, `admin`, `service` | `read` | No mutation |
| Admin replay/reindex controls | `admin` only | `admin` or `system:write` | Internal ops endpoint, no business mutation |
| Internal ingest endpoint (optional) | `service`, `admin` | `write` or `system:write` | Disabled if stream subscriber is used exclusively |

Agent tokens:
- Agent principals can read only when role/scope policy allows and tenant matches.
- No anonymous access.

## 9) Event and Audit Ordering Guarantees

For observer-owned persistence path:
1. Validate + normalize source event.
2. Persist `ObservationSignal` (commit).
3. Upsert `ObserverState` snapshot (commit, same transaction when possible).
4. Write audit entry via `audit_logging`/`audit_bridge` (commit).
5. Publish observer lifecycle event (`observer.signal.ingested.v1`, `observer.snapshot.updated.v1`).

Guarantees:
- Durable state before observer event publication.
- Audit record references persisted signal/snapshot IDs.
- At-least-once event handling with idempotent write keys.

## 10) API Endpoints (MVP)

Base path: `/api/observer`

- `GET /signals`
  - filters: `tenant_id` (admin only override), `source_module`, `severity`, `entity_type`, `entity_id`, `from`, `to`, `limit`, `cursor`
- `GET /signals/{signal_id}`
- `GET /state`
  - returns tenant-global `ObserverState`
- `GET /state/entities/{entity_type}/{entity_id}`
- `GET /summary`
  - compact aggregate of current tenant observer state
- `POST /admin/replay` (admin-only internal)
  - triggers bounded re-ingest from offset/time window
- `POST /admin/reconcile` (admin-only internal)
  - runs snapshot polling reconciliation for tenant/window

API constraints:
- Read endpoints must be side-effect free.
- Admin endpoints are operational controls only; no source-module mutation.

## 11) Storage Model

### 11.1 PostgreSQL (durable)

- `observer_signals` (append-only)
- `observer_state_snapshots` (upserted latest snapshot per scope + optional history table)
- optional `observer_ingest_offsets` (consumer checkpoint by source stream partition/key)

Indexes (minimum):
- `observer_signals(tenant_id, occurred_at desc)`
- `observer_signals(tenant_id, source_module, occurred_at desc)`
- unique idempotency key index (see section 12)
- `observer_state_snapshots(tenant_id, scope_type, scope_entity_type, scope_entity_id)` unique

### 11.2 Redis (ephemeral)

- short-lived projection cache for `GET /summary`.
- replay/reconcile locks to avoid concurrent duplicate jobs.

### 11.3 EventStream

- observer lifecycle events only (not source-of-truth state).

## 12) Idempotency and Deduplication

Idempotency key derivation (priority order):
1. `source_event_id` if globally unique and trusted.
2. hash of `(tenant_id, source_module, source_event_type, entity_type, entity_id, occurred_at, payload_hash)`.

Behavior:
- Duplicate ingest -> no-op for `ObservationSignal`, optional `last_seen_at` metric increment.
- Snapshot updates check `last_signal_id` / `snapshot_version`; stale updates rejected.
- Replay jobs are safe to re-run for same range.

## 13) Verification Gates

### 13.1 Unit and contract tests

- adapter mapping tests per source module.
- tenant isolation tests (positive + cross-tenant forbidden).
- idempotency tests (duplicate event, replay window).
- ordering tests (signal persisted before observer lifecycle event publish).
- auth matrix tests for all observer endpoints.

### 13.2 Integration tests

- ingest from EventStream fixture -> snapshot projection correctness.
- polling reconciliation correctness under missed events.
- audit reference linkage validation.

### 13.3 Repo gates

- targeted: `PYTHONPATH=. pytest tests/modules/test_observer_core.py -q`
- targeted integration: `PYTHONPATH=. pytest tests/modules/test_observer_core_integration.py -q`
- required repo gate: `./scripts/run_rc_staging_gate.sh`

## 14) Rollout Phases

### Phase 0 - Schema and contracts
- add models/migrations, schemas, and adapter interfaces;
- no runtime wiring yet.

### Phase 1 - Passive ingestion
- subscribe to EventStream for a subset (`skill_engine`, `task_queue`, `system_health`, `immune_orchestrator`);
- expose read APIs behind feature flag `OBSERVER_CORE_ENABLED`.

### Phase 2 - Full source coverage + polling
- add remaining module adapters;
- enable anti-entropy polling and replay admin endpoints.

### Phase 3 - Hardening and SLO gates
- performance tuning, retention policies, and backfill reliability;
- finalize operational dashboards and alerting.

### Phase 4 - Discovery handoff (deferred consumer)
- Discovery Layer starts consuming Observer signals/snapshots only;
- Discovery remains external to Observer Core and does not write Observer state directly.

## 15) Discovery Layer Deferral (explicit)

Deferred to next step:
- no Discovery schemas, endpoints, storage, or scoring logic in this MVP;
- no direct dependency from Observer Core to Discovery runtime code;
- only compatibility contract now: Discovery may later subscribe to `observer.signal.ingested.v1` and read `ObserverState` APIs.
