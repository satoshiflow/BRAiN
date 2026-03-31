#!/usr/bin/env bash
set -euo pipefail

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-brain-postgres}"
DB_USER="${DB_USER:-brain}"
DB_NAME="${DB_NAME:-brain}"

echo "[reconcile] Using container=${POSTGRES_CONTAINER} db=${DB_NAME} user=${DB_USER}"

docker exec "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1 -c "
CREATE TABLE IF NOT EXISTS alembic_version (
  version_num VARCHAR(128) NOT NULL PRIMARY KEY
);
ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128);
"

docker exec "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1 -c "
ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS value_score DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS effort_saved_hours DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS complexity_level VARCHAR(32) NOT NULL DEFAULT 'medium';
ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS quality_impact DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS premium_tier VARCHAR(32) NOT NULL DEFAULT 'free';
ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS internal_credit_price DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS marketplace_listing_state VARCHAR(32) NOT NULL DEFAULT 'internal_only';
"

docker exec "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1 -c "
CREATE TABLE IF NOT EXISTS cognitive_assessments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id VARCHAR(64),
  mission_id VARCHAR(120),
  normalized_intent TEXT NOT NULL,
  perception JSONB NOT NULL DEFAULT '{}'::jsonb,
  association_trace JSONB NOT NULL DEFAULT '{}'::jsonb,
  evaluation_signal JSONB NOT NULL DEFAULT '{}'::jsonb,
  recommended_skill_candidates JSONB NOT NULL DEFAULT '[]'::jsonb,
  latest_skill_run_id UUID,
  latest_feedback_at TIMESTAMPTZ,
  latest_feedback_score DOUBLE PRECISION,
  latest_feedback_success BOOLEAN,
  created_by VARCHAR(120),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS cognitive_learning_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  assessment_id UUID NOT NULL REFERENCES cognitive_assessments(id) ON DELETE CASCADE,
  skill_run_id UUID NOT NULL,
  evaluation_result_id UUID,
  experience_record_id UUID,
  outcome_state VARCHAR(32) NOT NULL,
  overall_score DOUBLE PRECISION,
  success BOOLEAN NOT NULL DEFAULT false,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"

echo "[reconcile] Local schema reconciliation complete."
echo "[reconcile] Next recommended step: docker exec brain-backend sh -lc 'cd /app && alembic upgrade heads'"
