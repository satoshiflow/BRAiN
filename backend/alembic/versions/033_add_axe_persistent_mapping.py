"""Add AXE persistent mapping and learning tables.

Revision ID: 033_add_axe_persistent_mapping
Revises: 032_add_economy_layer
Create Date: 2026-03-11 11:45:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "033_add_axe_persistent_mapping"
down_revision: Union[str, None] = "032_add_economy_layer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS axe_mapping_sets (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            provider_model TEXT NOT NULL,
            sanitization_level TEXT NOT NULL CHECK (sanitization_level IN ('strict', 'moderate', 'none')),
            principal_hash TEXT NULL,
            session_hash TEXT NULL,
            tenant_id TEXT NULL,
            message_fingerprint TEXT NOT NULL,
            mapping_count INT NOT NULL CHECK (mapping_count >= 0),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT uq_axe_mapping_sets_req_provider_fingerprint UNIQUE (request_id, provider, message_fingerprint),
            CONSTRAINT ck_axe_mapping_sets_exp_after_create CHECK (expires_at > created_at)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_axe_mapping_sets_request_id ON axe_mapping_sets (request_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_axe_mapping_sets_created_at ON axe_mapping_sets (created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_axe_mapping_sets_provider_created ON axe_mapping_sets (provider, created_at DESC);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS axe_mapping_entries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            mapping_set_id UUID NOT NULL REFERENCES axe_mapping_sets(id) ON DELETE CASCADE,
            placeholder TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            original_hash TEXT NOT NULL,
            hash_key_version SMALLINT NOT NULL,
            preview_redacted TEXT NULL,
            ordinal INT NOT NULL CHECK (ordinal >= 0),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_axe_mapping_entries_placeholder UNIQUE (mapping_set_id, placeholder),
            CONSTRAINT uq_axe_mapping_entries_ordinal UNIQUE (mapping_set_id, ordinal)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_axe_mapping_entries_mapping_set ON axe_mapping_entries (mapping_set_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_axe_mapping_entries_entity_type ON axe_mapping_entries (entity_type);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS axe_deanonymization_attempts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id TEXT NOT NULL,
            mapping_set_id UUID NOT NULL REFERENCES axe_mapping_sets(id) ON DELETE RESTRICT,
            attempt_no INT NOT NULL CHECK (attempt_no >= 1),
            status TEXT NOT NULL CHECK (status IN ('success', 'partial', 'failed', 'skipped')),
            reason_code TEXT NULL,
            placeholder_count INT NOT NULL CHECK (placeholder_count >= 0),
            restored_count INT NOT NULL CHECK (restored_count >= 0 AND restored_count <= placeholder_count),
            unresolved_placeholders JSONB NOT NULL DEFAULT '[]'::jsonb,
            response_fingerprint TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_axe_deanon_idempotency_key UNIQUE (idempotency_key),
            CONSTRAINT uq_axe_deanon_request_mapping_attempt UNIQUE (request_id, mapping_set_id, attempt_no),
            CONSTRAINT ck_axe_deanon_unresolved_array CHECK (jsonb_typeof(unresolved_placeholders) = 'array')
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_axe_deanon_request_created ON axe_deanonymization_attempts (request_id, created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_axe_deanon_status_created ON axe_deanonymization_attempts (status, created_at DESC);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS axe_learning_candidates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            window_start TIMESTAMPTZ NOT NULL,
            window_end TIMESTAMPTZ NOT NULL,
            provider TEXT NOT NULL,
            pattern_name TEXT NOT NULL,
            sample_size INT NOT NULL CHECK (sample_size >= 0),
            failure_rate NUMERIC(6,5) NOT NULL CHECK (failure_rate >= 0 AND failure_rate <= 1),
            confidence_score NUMERIC(6,5) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
            risk_score NUMERIC(6,5) NOT NULL CHECK (risk_score >= 0 AND risk_score <= 1),
            proposed_change JSONB NOT NULL,
            gate_state TEXT NOT NULL CHECK (gate_state IN ('pending_auto_gate', 'needs_human_review', 'approved', 'rejected', 'expired')),
            approved_by TEXT NULL,
            approved_at TIMESTAMPTZ NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_axe_learning_window_provider_pattern UNIQUE (window_start, window_end, provider, pattern_name),
            CONSTRAINT ck_axe_learning_window_order CHECK (window_end > window_start)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_axe_learning_window ON axe_learning_candidates (window_start DESC, window_end DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_axe_learning_gate_state ON axe_learning_candidates (gate_state, created_at DESC);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS axe_data_retention_runs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_started_at TIMESTAMPTZ NOT NULL,
            run_finished_at TIMESTAMPTZ NULL,
            deleted_mapping_sets INT NOT NULL DEFAULT 0,
            deleted_attempts INT NOT NULL DEFAULT 0,
            deleted_candidates INT NOT NULL DEFAULT 0,
            status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
            error_summary TEXT NULL
        );
        """
    )


def downgrade() -> None:
    op.drop_table("axe_data_retention_runs")
    op.drop_index("idx_axe_learning_gate_state", table_name="axe_learning_candidates")
    op.drop_index("idx_axe_learning_window", table_name="axe_learning_candidates")
    op.drop_table("axe_learning_candidates")
    op.drop_index("idx_axe_deanon_status_created", table_name="axe_deanonymization_attempts")
    op.drop_index("idx_axe_deanon_request_created", table_name="axe_deanonymization_attempts")
    op.drop_table("axe_deanonymization_attempts")
    op.drop_index("idx_axe_mapping_entries_entity_type", table_name="axe_mapping_entries")
    op.drop_index("idx_axe_mapping_entries_mapping_set", table_name="axe_mapping_entries")
    op.drop_table("axe_mapping_entries")
    op.drop_index("idx_axe_mapping_sets_provider_created", table_name="axe_mapping_sets")
    op.drop_index("idx_axe_mapping_sets_created_at", table_name="axe_mapping_sets")
    op.drop_index("idx_axe_mapping_sets_request_id", table_name="axe_mapping_sets")
    op.drop_table("axe_mapping_sets")
