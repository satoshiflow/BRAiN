# Skill Value Local DB Patch Runbook

This runbook documents a local recovery step for environments where ControlDeck v3 Skills pages return `500` after introducing Skill Value fields.

## Symptom

- `GET /api/skill-definitions` fails with `500`
- ControlDeck v3 `Skills` page shows `Konnte Skills-Daten nicht laden`

## Root cause

Local database schema is behind current backend code and misses new columns on `skill_definitions`:

- `value_score`
- `effort_saved_hours`
- `complexity_level`
- `quality_impact`
- `premium_tier`
- `internal_credit_price`
- `marketplace_listing_state`

Canonical migration for these fields:

- `backend/alembic/versions/048_add_skill_value_fields.py`
- `backend/alembic/versions/049_add_skill_premium_metadata.py`

## Preferred fix

Run Alembic against a clean/local-aligned DB state.

```bash
docker exec brain-backend sh -lc "cd /app && alembic upgrade heads"
```

For recurring local drift, run the reconciliation helper first:

```bash
./scripts/reconcile_local_db_schema.sh
```

Then verify Alembic head consistency:

```bash
./scripts/alembic_doctor.sh check
```

If heads are missing in `alembic_version`:

```bash
./scripts/alembic_doctor.sh reconcile
```

## Fallback fix (local patch)

Use only when migration history in local DB is inconsistent and blocks normal upgrade.

```bash
docker exec brain-postgres psql -U brain -d brain -c "ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS value_score DOUBLE PRECISION NOT NULL DEFAULT 0; ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS effort_saved_hours DOUBLE PRECISION NOT NULL DEFAULT 0; ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS complexity_level VARCHAR(32) NOT NULL DEFAULT 'medium'; ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS quality_impact DOUBLE PRECISION NOT NULL DEFAULT 0;"
```

For premium metadata drift:

```bash
docker exec brain-postgres psql -U brain -d brain -c "ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS premium_tier VARCHAR(32) NOT NULL DEFAULT 'free'; ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS internal_credit_price DOUBLE PRECISION NOT NULL DEFAULT 0; ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS marketplace_listing_state VARCHAR(32) NOT NULL DEFAULT 'internal_only';"
```

## Verification

1) Login and fetch token:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"admin123"}'
```

2) Check skill definitions endpoint:

```bash
curl "http://localhost:8000/api/skill-definitions?sort_by=value_score" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Expected: HTTP `200` and non-empty/valid JSON payload.
