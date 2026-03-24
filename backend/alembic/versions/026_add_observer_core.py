"""Add observer core signal and snapshot persistence.

Revision ID: 026_add_observer_core
Revises: 025_add_experience_layer
Create Date: 2026-03-09 16:55:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "026_add_observer_core"
down_revision: Union[str, None] = "025_add_experience_layer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS observer_signals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64) NOT NULL,
            source_module VARCHAR(120) NOT NULL,
            source_event_type VARCHAR(160) NOT NULL,
            source_event_id VARCHAR(160),
            correlation_id VARCHAR(160),
            entity_type VARCHAR(64) NOT NULL,
            entity_id VARCHAR(160) NOT NULL,
            signal_class VARCHAR(32) NOT NULL,
            severity VARCHAR(16) NOT NULL,
            occurred_at TIMESTAMPTZ NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            payload JSONB NOT NULL DEFAULT '{}',
            payload_hash VARCHAR(64) NOT NULL,
            ordering_key VARCHAR(160),
            idempotency_key VARCHAR(255) NOT NULL UNIQUE
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_observer_signals_tenant_occurred ON observer_signals (tenant_id, occurred_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_observer_signals_tenant_source ON observer_signals (tenant_id, source_module, occurred_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_observer_signals_entity ON observer_signals (tenant_id, entity_type, entity_id, occurred_at DESC);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS observer_state_snapshots (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64) NOT NULL,
            scope_type VARCHAR(32) NOT NULL DEFAULT 'tenant_global',
            scope_entity_type VARCHAR(64) NOT NULL DEFAULT '',
            scope_entity_id VARCHAR(160) NOT NULL DEFAULT '',
            snapshot_version INTEGER NOT NULL DEFAULT 1,
            last_signal_id UUID,
            last_occurred_at TIMESTAMPTZ,
            health_summary JSONB NOT NULL DEFAULT '{}',
            risk_summary JSONB NOT NULL DEFAULT '{}',
            execution_summary JSONB NOT NULL DEFAULT '{}',
            queue_summary JSONB NOT NULL DEFAULT '{}',
            audit_refs JSONB NOT NULL DEFAULT '[]',
            snapshot_payload JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_observer_state_scope UNIQUE (tenant_id, scope_type, scope_entity_type, scope_entity_id)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_observer_state_tenant_scope ON observer_state_snapshots (tenant_id, scope_type);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_observer_state_tenant_entity ON observer_state_snapshots (tenant_id, scope_entity_type, scope_entity_id);")

    op.execute(
        """
        INSERT INTO module_lifecycle (
            id, module_id, owner_scope, classification, lifecycle_status, canonical_path,
            active_routes, data_owner, auth_surface, event_contract_status, audit_policy,
            migration_adapter, kill_switch, replacement_target, sunset_phase, notes,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            'observer_core',
            'system',
            'NEW',
            'experimental',
            'backend/app/modules/observer_core',
            '["/api/observer/signals", "/api/observer/state", "/api/observer/summary"]'::jsonb,
            'observer_core',
            'viewer+operator+admin+service',
            'partial',
            'audit_required',
            'app.modules.observer_core',
            NULL,
            NULL,
            'phase_p1b',
            'Read-only observer API over normalized runtime signals and snapshots',
            NOW(),
            NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM module_lifecycle existing WHERE existing.module_id = 'observer_core'
        );
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM module_lifecycle WHERE module_id = 'observer_core';")
    op.execute("DROP INDEX IF EXISTS ix_observer_state_tenant_entity;")
    op.execute("DROP INDEX IF EXISTS ix_observer_state_tenant_scope;")
    op.drop_table("observer_state_snapshots")
    op.execute("DROP INDEX IF EXISTS ix_observer_signals_entity;")
    op.execute("DROP INDEX IF EXISTS ix_observer_signals_tenant_source;")
    op.execute("DROP INDEX IF EXISTS ix_observer_signals_tenant_occurred;")
    op.drop_table("observer_signals")
