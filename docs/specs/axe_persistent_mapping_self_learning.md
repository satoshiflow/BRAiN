# AXE Persistent Mapping and Self-Learning Loop (High Priority)

## Intent

Provide a durable mapping layer for AXE request-sanitization and response-deanonymization, then use failures and outcomes as learning signals for BRAIN evolution.

## Why now

- Current mapping is in-memory per request and is lost after response delivery.
- Cloud-provider safety requires traceability for deanonymization correctness.
- BRAIN learning model needs durable error/decision artifacts for offline analysis cycles.

## Scope

1. Persist request/response placeholder mappings in PostgreSQL.
2. Track deanonymization failures and ambiguity cases as first-class events.
3. Add offline analysis job to extract pattern improvements during low-traffic windows.
4. Enforce retention and privacy boundaries (hashing, deletion windows, minimal exposure).

## Contracts

### Request lifecycle

1. AXE chat request enters fusion service.
2. Sanitizer replaces sensitive values with placeholders.
3. Mapping rows are stored with `request_id` and provider metadata.
4. Provider response arrives.
5. Deanonymization restores placeholders.
6. Outcome row is stored (`success`, `partial`, `failed`) with reason code.

### Storage ownership

- PostgreSQL is source of truth for durable mapping/outcome records.
- Redis may cache short-lived lookup accelerators but is never the canonical store.

## Data model (initial)

### `axe_sanitization_mapping_logs`

- `id` (uuid pk)
- `request_id` (text, indexed)
- `session_id` (text, nullable)
- `user_id_hash` (text, nullable)
- `provider` (text)
- `placeholder` (text)
- `original_value_hash` (text)
- `original_preview` (text, nullable, truncated)
- `created_at` (timestamptz)

### `axe_deanonymization_outcomes`

- `id` (uuid pk)
- `request_id` (text, indexed)
- `provider` (text)
- `status` (`success|partial|failed`)
- `reason_code` (text, nullable)
- `placeholder_count` (int)
- `restored_count` (int)
- `created_at` (timestamptz)

### `axe_sanitization_insights`

- `id` (uuid pk)
- `window_start` (timestamptz)
- `window_end` (timestamptz)
- `provider` (text)
- `pattern_name` (text)
- `failure_rate` (numeric)
- `proposed_change` (jsonb)
- `approved` (bool default false)
- `created_at` (timestamptz)

## Privacy and governance

- Never store raw secrets or full PII in persistent tables.
- Store hashed originals and optional short previews with strong truncation.
- Define retention policy:
  - successful mappings: 30 days
  - partial/failed outcomes: 90 days
  - approved insight artifacts: 180 days (non-sensitive only)

## Runtime API additions

- Internal service methods:
  - `record_sanitization_mapping(request_id, mapping, provider, principal)`
  - `record_deanonymization_outcome(request_id, status, reason_code, stats)`
- Optional admin endpoint (phase 2):
  - `GET /api/axe/sanitization/insights`
  - `POST /api/axe/sanitization/insights/{id}/approve`

## Batch learning job

- Daily low-traffic job analyzes recent outcomes by provider and pattern.
- Produces candidate rule updates with confidence score.
- Human/operator approval gate required before activating new sanitization rules.

## Risks

- Overfitting sanitizer to one provider response style.
- Excessive logging accidentally leaking sensitive context.
- Deanonymization errors harming user usability if mappings drift.

## Done criteria

1. Mappings persist and are queryable by `request_id`.
2. Outcome telemetry exists for every sanitized cloud call.
3. Retention cleanup job runs and is test-covered.
4. Offline insight generation produces deterministic artifacts.
5. No raw sensitive values persist in storage.
