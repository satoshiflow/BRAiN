# Local DB Migration Repair Runbook

Status: Active  
Date: 2026-04-01

## Purpose

Repair stale local schema states that break runtime-control, AXE worker bridge, and audit/control-plane event paths.

Typical symptoms:

- `relation "control_plane_events" does not exist`
- `relation "audit_events" does not exist`
- `column axe_chat_sessions.tenant_id does not exist`
- `relation "brain_parameters" does not exist`

## Preconditions

- Local stack running with Docker Compose (`brain-backend`, `brain-postgres`)
- `.env.local` configured

## Fast Repair (recommended)

Run from repo root:

```bash
./scripts/alembic_doctor.sh reconcile
docker exec brain-backend sh -lc "cd /app && alembic upgrade heads"
```

What this does:

1. stamps missing alembic heads where local drift exists
2. applies schema reconciliation script
3. ensures alembic revision table shape
4. then attempts normal migration flow

## What gets reconciled explicitly

`./scripts/reconcile_local_db_schema.sh` now ensures these local-critical objects exist:

- `control_plane_events` (+ indexes)
- `audit_events` (+ indexes)
- `axe_chat_sessions.tenant_id`
- `brain_parameters`
- cognitive tables and skill value metadata columns

## Validation

Run these checks:

```bash
./scripts/alembic_doctor.sh check
docker exec brain-postgres psql -U brain -d brain -c "SELECT to_regclass('public.control_plane_events'), to_regclass('public.audit_events'), to_regclass('public.brain_parameters');"
./scripts/smoke_external_executors.sh
```

Expected results:

- alembic doctor returns `OK`
- all `to_regclass(...)` rows are non-null
- external smoke passes for OpenClaw + Paperclip

## Notes

- For local admin accounts without tenant binding, runtime-control overrides for this smoke flow should use `tenant_scope=system`.
- This runbook is for local repair. In shared/prod-like environments, use controlled migration rollout and backups first.
