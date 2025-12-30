"""Add audit trail schema for constitutional agents

Revision ID: 002_audit_trail
Revises: 001_initial_schema
Create Date: 2023-12-20 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '002_audit_trail'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    """Create audit trail tables for constitutional agents."""

    # ========================================================================
    # Supervision Audit Trail
    # ========================================================================

    op.create_table(
        'supervision_audit',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('audit_id', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, default=datetime.utcnow, index=True),

        # Request Info
        sa.Column('requesting_agent', sa.String(100), nullable=False, index=True),
        sa.Column('action', sa.String(200), nullable=False, index=True),
        sa.Column('risk_level', sa.String(20), nullable=False, index=True),
        sa.Column('context', JSONB, nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),

        # Response Info
        sa.Column('approved', sa.Boolean(), nullable=False, index=True),
        sa.Column('denial_reason', sa.Text(), nullable=True),
        sa.Column('human_oversight_required', sa.Boolean(), default=False, index=True),
        sa.Column('human_oversight_token', sa.String(100), nullable=True, unique=True),

        # Policy Evaluation
        sa.Column('policy_violations', JSONB, nullable=True),
        sa.Column('policy_effect', sa.String(20), nullable=True),

        # Metadata
        sa.Column('llm_response', sa.Text(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('metadata', JSONB, nullable=True),

        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow)
    )

    # Indexes for common queries
    op.create_index('idx_supervision_audit_timestamp_desc', 'supervision_audit', ['timestamp'], postgresql_ops={'timestamp': 'DESC'})
    op.create_index('idx_supervision_audit_approved', 'supervision_audit', ['approved'])
    op.create_index('idx_supervision_audit_risk_level', 'supervision_audit', ['risk_level'])
    op.create_index('idx_supervision_audit_agent_action', 'supervision_audit', ['requesting_agent', 'action'])


    # ========================================================================
    # Human Oversight Approvals
    # ========================================================================

    op.create_table(
        'human_oversight_approvals',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('token', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('audit_id', sa.String(100), sa.ForeignKey('supervision_audit.audit_id'), nullable=False),

        # Approval Info
        sa.Column('status', sa.String(20), nullable=False, default='pending', index=True),  # pending/approved/denied
        sa.Column('approved_by', sa.String(100), nullable=True),
        sa.Column('approval_timestamp', sa.DateTime(), nullable=True),
        sa.Column('approval_reason', sa.Text(), nullable=True),

        # Original Request (denormalized for quick access)
        sa.Column('requesting_agent', sa.String(100), nullable=False),
        sa.Column('action', sa.String(200), nullable=False),
        sa.Column('risk_level', sa.String(20), nullable=False),

        # Expiration
        sa.Column('expires_at', sa.DateTime(), nullable=True, index=True),

        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    )

    # Index for pending approvals
    op.create_index('idx_hitl_pending', 'human_oversight_approvals', ['status', 'expires_at'])


    # ========================================================================
    # Agent Actions Log
    # ========================================================================

    op.create_table(
        'agent_actions_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, default=datetime.utcnow, index=True),

        # Agent Info
        sa.Column('agent_id', sa.String(100), nullable=False, index=True),
        sa.Column('agent_type', sa.String(50), nullable=True),

        # Action Info
        sa.Column('action', sa.String(200), nullable=False, index=True),
        sa.Column('action_type', sa.String(50), nullable=True, index=True),  # code_generation, deployment, etc.
        sa.Column('result', sa.String(20), nullable=False, index=True),  # success, failure, cancelled

        # Details
        sa.Column('input_data', JSONB, nullable=True),
        sa.Column('output_data', JSONB, nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),

        # Supervision Link
        sa.Column('supervision_audit_id', sa.String(100), sa.ForeignKey('supervision_audit.audit_id'), nullable=True),

        # Metadata
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('metadata', JSONB, nullable=True),

        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow)
    )

    # Indexes for analytics
    op.create_index('idx_agent_actions_timestamp_desc', 'agent_actions_log', ['timestamp'], postgresql_ops={'timestamp': 'DESC'})
    op.create_index('idx_agent_actions_result', 'agent_actions_log', ['result'])
    op.create_index('idx_agent_actions_agent_type', 'agent_actions_log', ['agent_id', 'action_type'])


    # ========================================================================
    # Policy Evaluation Log
    # ========================================================================

    op.create_table(
        'policy_evaluation_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, default=datetime.utcnow, index=True),

        # Request
        sa.Column('agent_id', sa.String(100), nullable=False, index=True),
        sa.Column('action', sa.String(200), nullable=False),
        sa.Column('context', JSONB, nullable=True),

        # Evaluation Result
        sa.Column('effect', sa.String(20), nullable=False, index=True),  # allow, deny, warn
        sa.Column('matched_rule_id', sa.String(100), nullable=True, index=True),
        sa.Column('reason', sa.Text(), nullable=True),

        # Link to supervision
        sa.Column('supervision_audit_id', sa.String(100), sa.ForeignKey('supervision_audit.audit_id'), nullable=True),

        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow)
    )

    # Index for policy analytics
    op.create_index('idx_policy_eval_effect', 'policy_evaluation_log', ['effect'])
    op.create_index('idx_policy_eval_rule', 'policy_evaluation_log', ['matched_rule_id'])


    # ========================================================================
    # Compliance Reports
    # ========================================================================

    op.create_table(
        'compliance_reports',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('report_id', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, default=datetime.utcnow, index=True),

        # Report Type
        sa.Column('report_type', sa.String(50), nullable=False, index=True),  # dsgvo, eu_ai_act, security
        sa.Column('framework', sa.String(50), nullable=False, index=True),

        # System Under Review
        sa.Column('system_name', sa.String(200), nullable=False),
        sa.Column('architecture_spec', JSONB, nullable=True),

        # Compliance Results
        sa.Column('compliance_score', sa.Integer(), nullable=True),  # 0-100
        sa.Column('compliant', sa.Boolean(), nullable=False, index=True),
        sa.Column('violations', JSONB, nullable=True),
        sa.Column('recommendations', JSONB, nullable=True),

        # Detailed Findings
        sa.Column('findings', JSONB, nullable=True),
        sa.Column('prohibited_practices', JSONB, nullable=True),

        # Generated By
        sa.Column('generated_by_agent', sa.String(100), nullable=False),

        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow)
    )

    # Index for compliance analytics
    op.create_index('idx_compliance_timestamp_desc', 'compliance_reports', ['timestamp'], postgresql_ops={'timestamp': 'DESC'})
    op.create_index('idx_compliance_framework', 'compliance_reports', ['framework'])
    op.create_index('idx_compliance_score', 'compliance_reports', ['compliant', 'compliance_score'])


def downgrade():
    """Drop all audit trail tables."""
    op.drop_table('compliance_reports')
    op.drop_table('policy_evaluation_log')
    op.drop_table('agent_actions_log')
    op.drop_table('human_oversight_approvals')
    op.drop_table('supervision_audit')
