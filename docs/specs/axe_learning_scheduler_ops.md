# AXE Learning Scheduler Ops Guide

## Purpose

Operational guide for enabling and monitoring the AXE persistent-mapping learning loop in backend environments.

## Components

- Worker: `backend/app/workers/axe_learning_scheduler.py`
- Runtime wiring: `backend/main.py` (lifespan-managed)
- Service orchestration: `backend/app/modules/axe_fusion/service.py`
- Persistence/repository: `backend/app/modules/axe_fusion/mapping_repository.py`
- Admin APIs: `backend/app/modules/axe_fusion/router.py`

## Environment Variables

- `ENABLE_AXE_LEARNING_SCHEDULER` (`true|false`, default `false`)
- `AXE_LEARNING_INTERVAL_SECONDS` (default `3600`)
- `AXE_LEARNING_WINDOW_DAYS` (default `7`)
- `AXE_LEARNING_MIN_SAMPLE_SIZE` (default `50`)
- `AXE_MAPPING_HASH_KEY` (required in production; rotate via key-versioning)
- `AXE_MAPPING_HASH_KEY_VERSION` (default `1`)

## Activation

1. Ensure migration `033_add_axe_persistent_mapping` is present in deployed image.
2. Set `AXE_MAPPING_HASH_KEY` with a non-default secret.
3. Enable scheduler with `ENABLE_AXE_LEARNING_SCHEDULER=true`.
4. Restart backend process.
5. Validate logs for startup line: `AXE learning scheduler started`.

## Manual Operations

Use role-protected AXE admin endpoints:

- Generate candidates:
  - `POST /api/axe/admin/sanitization/insights/generate?window_days=7&min_sample_size=50`
- List candidates:
  - `GET /api/axe/admin/sanitization/insights`
- Approve/reject candidate:
  - `POST /api/axe/admin/sanitization/insights/{id}/approve`
  - `POST /api/axe/admin/sanitization/insights/{id}/reject`
- Run retention:
  - `POST /api/axe/admin/retention/run`

All mutations emit unified audit events with `event_type=axe.admin`.

## Monitoring

Track periodically:

- Growth of `axe_mapping_sets` and `axe_deanonymization_attempts`
- Candidate backlog by `gate_state`
- Retention deletion counts in `axe_data_retention_runs`

Recommended alerts:

- Retention failures (`status=failed` in retention runs)
- Candidate generation creates zero entries for > 3 consecutive cycles
- Sudden spike in `failed|partial` deanonymization outcomes

## Safety Notes

- Never persist raw sensitive values; only hashes/previews are stored.
- Keep scheduler disabled in ephemeral test runs unless validating analytics behavior.
- Approval endpoints are governance-sensitive; require operator/admin/system_admin roles.
