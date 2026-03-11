# AXE Persistent Mapping + Self-Learning (Production Backend Spec)

## Intent

Create a durable, privacy-safe mapping ledger for AXE sanitization/deanonymization and a governed learning loop that improves rules without unsafe automatic rollout.

## Scope (v1)

1. Persist sanitization mapping metadata and deanonymization outcomes in PostgreSQL.
2. Guarantee idempotent outcome recording per request/attempt.
3. Add privacy controls (hashing, key versioning, retention, audit trail).
4. Add offline learning pipeline with confidence gates and human approval.
5. Integrate with `backend/app/modules/axe_fusion/service.py` and new admin APIs.

## 1) Improved Schema (Tables / Indexes / Constraints)

PostgreSQL is canonical storage. Redis may cache `(request_id -> active_mapping_set_id)` for latency only.

### `axe_mapping_sets`

One row per sanitized outbound call.

- `id uuid primary key default gen_random_uuid()`
- `request_id text not null`
- `provider text not null`
- `provider_model text not null`
- `sanitization_level text not null check (sanitization_level in ('strict','standard','none'))`
- `principal_hash text null`
- `session_hash text null`
- `tenant_id text null`
- `message_fingerprint text not null` (hash of normalized outbound prompt)
- `mapping_count int not null check (mapping_count >= 0)`
- `created_at timestamptz not null default now()`
- `expires_at timestamptz not null`

Indexes / constraints:

- `unique (request_id, provider, message_fingerprint)` (dedupe retries)
- `index idx_axe_mapping_sets_request_id (request_id)`
- `index idx_axe_mapping_sets_created_at (created_at desc)`
- `index idx_axe_mapping_sets_provider_created (provider, created_at desc)`
- `check (expires_at > created_at)`

### `axe_mapping_entries`

One row per placeholder inside a mapping set.

- `id uuid primary key default gen_random_uuid()`
- `mapping_set_id uuid not null references axe_mapping_sets(id) on delete cascade`
- `placeholder text not null`
- `entity_type text not null` (email, phone, token, address, person_name, etc.)
- `original_hash text not null` (HMAC digest)
- `hash_key_version smallint not null`
- `preview_redacted text null` (max 24 chars, masked)
- `ordinal int not null check (ordinal >= 0)`
- `created_at timestamptz not null default now()`

Indexes / constraints:

- `unique (mapping_set_id, placeholder)`
- `unique (mapping_set_id, ordinal)`
- `index idx_axe_mapping_entries_mapping_set (mapping_set_id)`
- `index idx_axe_mapping_entries_entity_type (entity_type)`

### `axe_deanonymization_attempts`

Outcome telemetry per provider response handling attempt.

- `id uuid primary key default gen_random_uuid()`
- `request_id text not null`
- `mapping_set_id uuid not null references axe_mapping_sets(id) on delete restrict`
- `attempt_no int not null check (attempt_no >= 1)`
- `status text not null check (status in ('success','partial','failed','skipped'))`
- `reason_code text null` (`PLACEHOLDER_MISSING`, `COLLISION`, `AMBIGUOUS_MATCH`, `MAPPING_NOT_FOUND`, `TIMEOUT`...)
- `placeholder_count int not null check (placeholder_count >= 0)`
- `restored_count int not null check (restored_count >= 0 and restored_count <= placeholder_count)`
- `unresolved_placeholders jsonb not null default '[]'::jsonb`
- `response_fingerprint text not null` (hash of provider response before restore)
- `idempotency_key text not null`
- `created_at timestamptz not null default now()`

Indexes / constraints:

- `unique (idempotency_key)`
- `unique (request_id, mapping_set_id, attempt_no)`
- `index idx_axe_deanon_request_created (request_id, created_at desc)`
- `index idx_axe_deanon_status_created (status, created_at desc)`
- `check (jsonb_typeof(unresolved_placeholders) = 'array')`

### `axe_learning_candidates`

Offline generated rule proposals.

- `id uuid primary key default gen_random_uuid()`
- `window_start timestamptz not null`
- `window_end timestamptz not null`
- `provider text not null`
- `pattern_name text not null`
- `sample_size int not null check (sample_size >= 0)`
- `failure_rate numeric(6,5) not null check (failure_rate >= 0 and failure_rate <= 1)`
- `confidence_score numeric(6,5) not null check (confidence_score >= 0 and confidence_score <= 1)`
- `risk_score numeric(6,5) not null check (risk_score >= 0 and risk_score <= 1)`
- `proposed_change jsonb not null`
- `gate_state text not null check (gate_state in ('pending_auto_gate','needs_human_review','approved','rejected','expired'))`
- `approved_by text null`
- `approved_at timestamptz null`
- `created_at timestamptz not null default now()`

Indexes / constraints:

- `index idx_axe_learning_window (window_start desc, window_end desc)`
- `index idx_axe_learning_gate_state (gate_state, created_at desc)`
- `unique (window_start, window_end, provider, pattern_name)`
- `check (window_end > window_start)`

### `axe_data_retention_runs`

Retention/audit trace for deletion jobs.

- `id uuid primary key default gen_random_uuid()`
- `run_started_at timestamptz not null`
- `run_finished_at timestamptz null`
- `deleted_mapping_sets int not null default 0`
- `deleted_attempts int not null default 0`
- `deleted_candidates int not null default 0`
- `status text not null check (status in ('running','succeeded','failed'))`
- `error_summary text null`

## 2) Privacy Model (Hash / Salt / Retention / Audit)

- Hashing: use `HMAC-SHA256(service_secret_vN, canonical_original_value)`; do not store raw values.
- Salt strategy: secret-managed keyed HMAC (pepper) + deterministic canonicalization (trim, Unicode normalize, lowercase where type-safe).
- Key versioning: persist `hash_key_version`; support rolling keys without rehashing old rows.
- Preview policy: `preview_redacted` optional, hard-capped, masked (`jo***@g***.com`); disabled by env in high-security tenants.
- Retention: mapping sets with only success outcomes 30d; partial/failed 90d; approved learning candidates 180d; retention runs logged forever (or compliance-specific).
- Deletion semantics: hard-delete mapping entries/sets by TTL; keep aggregate non-sensitive stats only.
- Tenant isolation: all admin queries filter by authorized tenant scope where `tenant_id` present.
- Audit events (mandatory): `axe.mapping_set.created`, `axe.deanonymization.attempt.recorded`, `axe.learning.candidate.generated`, `axe.learning.candidate.approved|rejected`, `axe.retention.run.completed`.

## 3) Learning-Loop Workflow with Confidence Gates

### Pipeline

1. Nightly batch loads last N days of `axe_deanonymization_attempts` + mapping metadata by provider/pattern.
2. Compute metrics: failure rate, ambiguity rate, unresolved placeholder classes, drift vs prior 7-day baseline.
3. Generate `proposed_change` artifact (rule delta + expected impact + rollback hint).
4. Score candidate (`confidence_score`, `risk_score`) and assign `gate_state`.

### Confidence gates

- Auto-reject if `sample_size < 200` or high-risk entity types affected.
- Auto-reject if projected false-positive risk > threshold.
- Send to human review when `0.70 <= confidence_score < 0.92` or `risk_score > 0.30`.
- Auto-approve only when all conditions pass:
  - `sample_size >= 1000`
  - `confidence_score >= 0.92`
  - `risk_score <= 0.15`
  - shadow replay success >= 99.5% on holdout set.
- Activation model: approved candidate creates versioned sanitizer ruleset (`draft -> active`), never in-place mutate active rules.

## 4) Failure Recovery + Idempotency (Deanonymization)

- Idempotency key format: `sha256(request_id + mapping_set_id + attempt_no + response_fingerprint)`.
- On retry from upstream timeout/network split, `INSERT ... ON CONFLICT(idempotency_key) DO NOTHING` then fetch existing attempt row.
- If mapping set missing:
  - mark attempt `failed/MAPPING_NOT_FOUND`
  - return sanitized provider text unchanged (fail-safe, no accidental reconstruction).
- If partial restore:
  - return partially restored text + unresolved placeholders in telemetry
  - never guess unresolved values.
- Exactly-once semantics for outcome recording at application level; at-least-once from transport tolerated by idempotency key.
- Recovery job (`axe_deanonymization_reconciler`): scans recent provider responses lacking outcome row and writes `failed/TIMEOUT_OR_INTERRUPT` for observability completeness.

## 5) Integration Touchpoints (`axe_fusion/service.py`, router/admin APIs)

### Service changes (`backend/app/modules/axe_fusion/service.py`)

- Add repository dependency (async): `AXEMappingRepository`.
- Add methods:
  - `record_sanitization_mapping(...) -> mapping_set_id`
  - `record_deanonymization_attempt(...) -> attempt_id`
  - `get_mapping_set_for_request(request_id, provider, message_fingerprint)`
- In `AXEFusionService.chat(...)` flow:
  1. sanitize outbound and persist mapping set before provider call.
  2. on provider response, deanonymize and persist attempt (`success|partial|failed`).
  3. on exceptions, persist `failed` attempt with reason code before raising.
- Pass `request_id` from router (`x-request-id` fallback generated UUID) into service.

### Router changes (`backend/app/modules/axe_fusion/router.py`)

- Extend `axe_chat` to create/propagate canonical `request_id` to service.
- Add safe response metadata header: `x-axe-request-id`.
- Keep user response schema stable; do not expose mapping internals.

### New admin router (`backend/app/modules/axe_fusion/admin_router.py`)

Role-gated (`OPERATOR|ADMIN|SYSTEM_ADMIN`), trust-validated, tenant-scoped.

- `GET /api/axe/admin/sanitization/insights?provider=&gate_state=&window_start=&window_end=`
- `POST /api/axe/admin/sanitization/insights/{id}/approve`
- `POST /api/axe/admin/sanitization/insights/{id}/reject`
- `GET /api/axe/admin/deanonymization/outcomes?request_id=&status=&from=&to=`
- `POST /api/axe/admin/retention/run` (manual trigger, audited)

All admin mutations emit audit events and require explicit reason payload.

## 6) Phased Implementation Plan + Tests

### Phase 0: Foundations

- Add SQL migrations for 5 tables, indexes, constraints.
- Implement repository layer with async SQLAlchemy and idempotent inserts.
- Tests:
  - migration applies cleanly
  - uniqueness/constraint enforcement
  - repository idempotency conflict behavior

### Phase 1: Runtime persistence in AXE chat path

- Wire `request_id` propagation from router to service.
- Persist mapping sets/entries + deanonymization attempts.
- Add structured reason codes and status mapping.
- Tests:
  - `AXEFusionService.chat` success persists set + success attempt
  - provider failure persists failed attempt
  - partial deanonymization persists unresolved placeholders
  - API test verifies stable response + `x-axe-request-id` header

### Phase 2: Retention + audit

- Add scheduled retention worker + manual admin trigger.
- Emit audit/events for create/attempt/approve/reject/retention.
- Tests:
  - TTL deletion windows by status
  - audit event emitted with required fields
  - tenant-scope enforcement for admin queries

### Phase 3: Learning loop + governance

- Implement nightly learning job and confidence scoring.
- Add admin approve/reject endpoints and versioned rule activation.
- Add shadow replay before activation.
- Tests:
  - deterministic candidate generation from fixture dataset
  - confidence gate transitions
  - activation creates new ruleset version only after approval
  - rollback path returns previous active ruleset

## Done Criteria

1. Every sanitized provider call has durable mapping metadata and deanonymization attempt telemetry.
2. No raw secrets/PII are persisted in AXE mapping tables.
3. Deanonymization attempt recording is idempotent under retries.
4. Learning candidates are confidence-scored and approval-gated before activation.
5. Retention and admin operations are audited and test-covered.
