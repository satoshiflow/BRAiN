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
CREATE TABLE IF NOT EXISTS control_plane_events (
  id UUID PRIMARY KEY,
  tenant_id VARCHAR(64),
  entity_type VARCHAR(64) NOT NULL,
  entity_id VARCHAR(160) NOT NULL,
  event_type VARCHAR(160) NOT NULL,
  correlation_id VARCHAR(160),
  mission_id VARCHAR(120),
  actor_id VARCHAR(120),
  actor_type VARCHAR(32),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  audit_required BOOLEAN NOT NULL DEFAULT FALSE,
  published BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  published_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_control_plane_events_tenant_id ON control_plane_events(tenant_id);
CREATE INDEX IF NOT EXISTS ix_control_plane_events_entity_type ON control_plane_events(entity_type);
CREATE INDEX IF NOT EXISTS ix_control_plane_events_entity_id ON control_plane_events(entity_id);
CREATE INDEX IF NOT EXISTS ix_control_plane_events_event_type ON control_plane_events(event_type);
CREATE INDEX IF NOT EXISTS ix_control_plane_events_correlation_id ON control_plane_events(correlation_id);
"

docker exec "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1 -c "
CREATE TABLE IF NOT EXISTS audit_events (
  id UUID PRIMARY KEY,
  event_type VARCHAR(50) NOT NULL,
  action VARCHAR(50) NOT NULL,
  actor VARCHAR(100) NOT NULL,
  actor_type VARCHAR(50) NOT NULL DEFAULT 'user',
  resource_type VARCHAR(100),
  resource_id VARCHAR(100),
  old_values JSONB,
  new_values JSONB,
  ip_address VARCHAR(45),
  user_agent TEXT,
  severity VARCHAR(20) NOT NULL DEFAULT 'info',
  message TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_audit_events_event_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS ix_audit_events_action ON audit_events(action);
CREATE INDEX IF NOT EXISTS ix_audit_events_actor ON audit_events(actor);
CREATE INDEX IF NOT EXISTS ix_audit_events_resource_type ON audit_events(resource_type);
"

docker exec "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1 -c "
ALTER TABLE IF EXISTS axe_chat_sessions ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(128);
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

docker exec "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1 -c "
CREATE TABLE IF NOT EXISTS brain_parameters (
  id UUID PRIMARY KEY,
  parameter_key VARCHAR(100) UNIQUE NOT NULL,
  parameter_value JSONB NOT NULL,
  parameter_type VARCHAR(20) DEFAULT 'float',
  min_value JSONB,
  max_value JSONB,
  default_value JSONB,
  description VARCHAR(500),
  is_mutable BOOLEAN DEFAULT TRUE,
  learning_enabled BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
"

echo "[reconcile] Local schema reconciliation complete."
echo "[reconcile] Next recommended step: docker exec brain-backend sh -lc 'cd /app && alembic upgrade heads'"
