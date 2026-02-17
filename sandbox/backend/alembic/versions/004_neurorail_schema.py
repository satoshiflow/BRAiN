"""Add NeuroRail and Governor schema

Revision ID: 004_neurorail_schema
Revises: 003_credit_snapshots_table
Create Date: 2025-12-30 14:00:00.000000

Creates tables for NeuroRail execution system:
- neurorail_audit: Immutable audit log for all execution events
- neurorail_state_transitions: State machine transition history
- governor_decisions: Governance and budget decisions
- neurorail_metrics_snapshots: Periodic metric snapshots
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '004_neurorail_schema'
down_revision = '003_credit_snapshots_table'
branch_labels = None
depends_on = None


def upgrade():
    """Create NeuroRail and Governor tables."""

    # ========================================================================
    # NeuroRail Audit Trail
    # ========================================================================

    op.create_table(
        'neurorail_audit',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('audit_id', sa.String(20), unique=True, nullable=False, index=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, default=datetime.utcnow, index=True),

        # Trace Context (hierarchical entity IDs)
        sa.Column('mission_id', sa.String(20), nullable=True, index=True),
        sa.Column('plan_id', sa.String(20), nullable=True, index=True),
        sa.Column('job_id', sa.String(20), nullable=True, index=True),
        sa.Column('attempt_id', sa.String(20), nullable=True, index=True),
        sa.Column('resource_uuid', sa.String(20), nullable=True, index=True),

        # Event Details
        sa.Column('event_type', sa.String(50), nullable=False, index=True),
        # Event types: state_transition, resource_allocation, error, decision, budget_check, reflex_trigger
        sa.Column('event_category', sa.String(50), nullable=False, index=True),
        # Categories: execution, governance, safety, telemetry
        sa.Column('severity', sa.String(20), nullable=False, index=True),
        # Severity: info, warning, error, critical

        # Content
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', JSONB, nullable=True),
        # details can include: error_code, budget_consumed, state_from, state_to, etc.

        # Attribution
        sa.Column('caused_by_agent', sa.String(50), nullable=True),
        sa.Column('caused_by_event', sa.String(20), nullable=True),
        # Reference to another audit_id that triggered this event

        # Metadata
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow)
    )

    # Indexes for query performance
    op.create_index('idx_neurorail_audit_timestamp_desc', 'neurorail_audit', ['timestamp'], postgresql_ops={'timestamp': 'DESC'})
    op.create_index('idx_neurorail_audit_mission', 'neurorail_audit', ['mission_id', 'timestamp'])
    op.create_index('idx_neurorail_audit_event_type', 'neurorail_audit', ['event_type'])
    op.create_index('idx_neurorail_audit_severity', 'neurorail_audit', ['severity'])
    op.create_index('idx_neurorail_audit_category', 'neurorail_audit', ['event_category'])
    op.create_index('idx_neurorail_audit_job', 'neurorail_audit', ['job_id', 'timestamp'])


    # ========================================================================
    # NeuroRail State Transitions
    # ========================================================================

    op.create_table(
        'neurorail_state_transitions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.String(20), unique=True, nullable=False, index=True),

        # Entity
        sa.Column('entity_type', sa.String(20), nullable=False, index=True),
        # Entity types: mission, plan, job, attempt
        sa.Column('entity_id', sa.String(20), nullable=False, index=True),

        # State Transition
        sa.Column('from_state', sa.String(30), nullable=True),
        # from_state is nullable for initial state (creation)
        sa.Column('to_state', sa.String(30), nullable=False),
        sa.Column('transition', sa.String(30), nullable=False),
        # Transitions: create, start, complete, fail, timeout, cancel, retry

        # Timing
        sa.Column('timestamp', sa.DateTime(), nullable=False, default=datetime.utcnow, index=True),

        # Context
        sa.Column('metadata', JSONB, nullable=True),
        # metadata can include: reason, error_code, budget_snapshot, etc.
        sa.Column('caused_by', sa.String(20), nullable=True),
        # Reference to event_id that caused this transition

        # Metadata
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow)
    )

    # Indexes for state machine queries
    op.create_index('idx_state_transitions_entity', 'neurorail_state_transitions', ['entity_type', 'entity_id'])
    op.create_index('idx_state_transitions_timestamp_desc', 'neurorail_state_transitions', ['timestamp'], postgresql_ops={'timestamp': 'DESC'})
    op.create_index('idx_state_transitions_to_state', 'neurorail_state_transitions', ['to_state'])
    op.create_index('idx_state_transitions_entity_timestamp', 'neurorail_state_transitions', ['entity_id', 'timestamp'])


    # ========================================================================
    # Governor Decisions
    # ========================================================================

    op.create_table(
        'governor_decisions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('decision_id', sa.String(20), unique=True, nullable=False, index=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, default=datetime.utcnow, index=True),

        # Decision Type
        sa.Column('decision_type', sa.String(50), nullable=False, index=True),
        # Types: budget_check, policy_evaluation, mode_decision, retry_decision, manifest_shadow

        # Context
        sa.Column('context', JSONB, nullable=False),
        # context includes: entity_ids, budget_snapshot, policy_context, etc.

        # Decision
        sa.Column('allowed', sa.Boolean(), nullable=False, index=True),
        sa.Column('reason', sa.Text(), nullable=False),

        # Enforcement Actions
        sa.Column('actions', JSONB, nullable=True),
        # actions: ["cancel_job", "reduce_timeout", "escalate_to_human", "apply_cooldown"]

        # Trace Context
        sa.Column('mission_id', sa.String(20), nullable=True, index=True),
        sa.Column('plan_id', sa.String(20), nullable=True),
        sa.Column('job_id', sa.String(20), nullable=True, index=True),

        # Manifest Shadow (for dry-run mode)
        sa.Column('manifest_version', sa.String(50), nullable=True),
        sa.Column('shadow_mode', sa.Boolean(), default=False, index=True),
        # shadow_mode=True means this was a dry-run evaluation

        # Metadata
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow)
    )

    # Indexes for governance queries
    op.create_index('idx_governor_decisions_timestamp_desc', 'governor_decisions', ['timestamp'], postgresql_ops={'timestamp': 'DESC'})
    op.create_index('idx_governor_decisions_mission', 'governor_decisions', ['mission_id'])
    op.create_index('idx_governor_decisions_type', 'governor_decisions', ['decision_type'])
    op.create_index('idx_governor_decisions_allowed', 'governor_decisions', ['allowed'])
    op.create_index('idx_governor_decisions_shadow', 'governor_decisions', ['shadow_mode', 'manifest_version'])


    # ========================================================================
    # NeuroRail Metrics Snapshots
    # ========================================================================

    op.create_table(
        'neurorail_metrics_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('snapshot_id', sa.String(20), unique=True, nullable=False, index=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, default=datetime.utcnow, index=True),

        # Entity
        sa.Column('entity_id', sa.String(20), nullable=False, index=True),
        sa.Column('entity_type', sa.String(20), nullable=False, index=True),
        # Entity types: mission, plan, job, attempt

        # Metrics (JSONB for flexibility)
        sa.Column('metrics', JSONB, nullable=False),
        # metrics structure:
        # {
        #   "started_at": "timestamp",
        #   "completed_at": "timestamp",
        #   "duration_ms": 1234.5,
        #   "llm_tokens_consumed": 500,
        #   "cpu_time_ms": 100.0,
        #   "memory_peak_mb": 50.0,
        #   "attempt_count": 3,
        #   "retry_count": 2,
        #   "success": true,
        #   "error_type": null,
        #   "error_category": null
        # }

        # Metadata
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow)
    )

    # Indexes for metrics queries
    op.create_index('idx_metrics_snapshots_entity', 'neurorail_metrics_snapshots', ['entity_type', 'entity_id'])
    op.create_index('idx_metrics_snapshots_timestamp_desc', 'neurorail_metrics_snapshots', ['timestamp'], postgresql_ops={'timestamp': 'DESC'})
    op.create_index('idx_metrics_snapshots_entity_timestamp', 'neurorail_metrics_snapshots', ['entity_id', 'timestamp'])


    # ========================================================================
    # Governor Manifest Versions (for shadow mode)
    # ========================================================================

    op.create_table(
        'governor_manifests',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('version', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('status', sa.String(20), nullable=False, index=True),
        # Status: shadow, active, deprecated

        # Manifest Content
        sa.Column('manifest', JSONB, nullable=False),
        # Full manifest specification (budget constraints, policies, etc.)

        # Shadow Evaluation
        sa.Column('shadow_started_at', sa.DateTime(), nullable=True),
        sa.Column('shadow_duration_hours', sa.Integer(), default=24),
        sa.Column('shadow_report', JSONB, nullable=True),
        # Shadow report includes: over_enforcement_ratio, impact_analysis, conflicts

        # Change Tracking
        sa.Column('changed_by', sa.String(100), nullable=False),
        sa.Column('change_reason', sa.Text(), nullable=False),
        sa.Column('prev_version', sa.String(50), nullable=True),
        # Reference to previous manifest version

        # Activation
        sa.Column('activated_at', sa.DateTime(), nullable=True),
        sa.Column('activated_by', sa.String(100), nullable=True),

        # Metadata
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    )

    # Indexes for manifest management
    op.create_index('idx_manifests_status', 'governor_manifests', ['status'])
    op.create_index('idx_manifests_shadow_started', 'governor_manifests', ['shadow_started_at'])


def downgrade():
    """Drop all NeuroRail and Governor tables."""
    op.drop_table('governor_manifests')
    op.drop_table('neurorail_metrics_snapshots')
    op.drop_table('governor_decisions')
    op.drop_table('neurorail_state_transitions')
    op.drop_table('neurorail_audit')
