"""Add fleet management tables for robots, tasks, and zones

Revision ID: 001_add_fleet_tables
Revises: fred_bridge_v1
Create Date: 2026-02-25 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_add_fleet_tables"
down_revision: Union[str, None] = "fred_bridge_v1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create fleets table
    op.create_table(
        "fleets",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("fleet_id", sa.String(100), nullable=False),
        sa.Column("owner_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(5000), nullable=True),
        sa.Column("max_robots", sa.Integer(), nullable=False),
        sa.Column("total_robots", sa.Integer(), nullable=False),
        sa.Column("online_robots", sa.Integer(), nullable=False),
        sa.Column("idle_robots", sa.Integer(), nullable=False),
        sa.Column("busy_robots", sa.Integer(), nullable=False),
        sa.Column("robots_in_error", sa.Integer(), nullable=False),
        sa.Column("average_battery_percentage", sa.Float(), nullable=False),
        sa.Column("total_tasks_queued", sa.Integer(), nullable=False),
        sa.Column("tasks_in_progress", sa.Integer(), nullable=False),
        sa.Column("tasks_completed_today", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fleet_id"),
    )
    op.create_index(op.f("ix_fleets_fleet_id"), "fleets", ["fleet_id"], unique=True)
    op.create_index(op.f("ix_fleets_owner_id"), "fleets", ["owner_id"])
    op.create_index(op.f("ix_fleets_created_at"), "fleets", ["created_at"])

    # Create robots table
    op.create_table(
        "robots",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("robot_id", sa.String(100), nullable=False),
        sa.Column("fleet_id", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("capabilities", postgresql.JSON(), nullable=False),
        sa.Column("state", sa.String(50), nullable=False),
        sa.Column("battery_percentage", sa.Float(), nullable=False),
        sa.Column("position", postgresql.JSON(), nullable=True),
        sa.Column("current_task_id", sa.String(100), nullable=True),
        sa.Column("uptime_hours", sa.Float(), nullable=False),
        sa.Column("tasks_completed_today", sa.Integer(), nullable=False),
        sa.Column("registered_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["fleet_id"], ["fleets.fleet_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("robot_id"),
    )
    op.create_index(op.f("ix_robots_robot_id"), "robots", ["robot_id"], unique=True)
    op.create_index(op.f("ix_robots_fleet_id"), "robots", ["fleet_id"])
    op.create_index(op.f("ix_robots_state"), "robots", ["state"])
    op.create_index(op.f("ix_robots_last_seen"), "robots", ["last_seen"])
    op.create_index("ix_robots_fleet_state", "robots", ["fleet_id", "state"])

    # Create fleet_tasks table
    op.create_table(
        "fleet_tasks",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("task_id", sa.String(100), nullable=False),
        sa.Column("fleet_id", sa.String(100), nullable=False),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("description", sa.String(5000), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("assigned_robot_id", sa.String(100), nullable=True),
        sa.Column("required_capabilities", postgresql.JSON(), nullable=False),
        sa.Column("target_position", postgresql.JSON(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("payload", postgresql.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["fleet_id"], ["fleets.fleet_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index(op.f("ix_fleet_tasks_task_id"), "fleet_tasks", ["task_id"], unique=True)
    op.create_index(op.f("ix_fleet_tasks_fleet_id"), "fleet_tasks", ["fleet_id"])
    op.create_index(op.f("ix_fleet_tasks_status"), "fleet_tasks", ["status"])
    op.create_index(op.f("ix_fleet_tasks_assigned_robot_id"), "fleet_tasks", ["assigned_robot_id"])
    op.create_index(op.f("ix_fleet_tasks_created_at"), "fleet_tasks", ["created_at"])
    op.create_index("ix_tasks_fleet_status", "fleet_tasks", ["fleet_id", "status"])

    # Create coordination_zones table
    op.create_table(
        "coordination_zones",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("zone_id", sa.String(100), nullable=False),
        sa.Column("zone_type", sa.String(100), nullable=False),
        sa.Column("max_concurrent_robots", sa.Integer(), nullable=False),
        sa.Column("coordinates", postgresql.JSON(), nullable=False),
        sa.Column("current_robots", postgresql.JSON(), nullable=False),
        sa.Column("waiting_robots", postgresql.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_modified", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("zone_id"),
    )
    op.create_index(op.f("ix_coordination_zones_zone_id"), "coordination_zones", ["zone_id"], unique=True)


def downgrade() -> None:
    # Drop coordination_zones table
    op.drop_index(op.f("ix_coordination_zones_zone_id"), table_name="coordination_zones")
    op.drop_table("coordination_zones")

    # Drop fleet_tasks table
    op.drop_index("ix_tasks_fleet_status", table_name="fleet_tasks")
    op.drop_index(op.f("ix_fleet_tasks_created_at"), table_name="fleet_tasks")
    op.drop_index(op.f("ix_fleet_tasks_assigned_robot_id"), table_name="fleet_tasks")
    op.drop_index(op.f("ix_fleet_tasks_status"), table_name="fleet_tasks")
    op.drop_index(op.f("ix_fleet_tasks_fleet_id"), table_name="fleet_tasks")
    op.drop_index(op.f("ix_fleet_tasks_task_id"), table_name="fleet_tasks")
    op.drop_table("fleet_tasks")

    # Drop robots table
    op.drop_index("ix_robots_fleet_state", table_name="robots")
    op.drop_index(op.f("ix_robots_last_seen"), table_name="robots")
    op.drop_index(op.f("ix_robots_state"), table_name="robots")
    op.drop_index(op.f("ix_robots_fleet_id"), table_name="robots")
    op.drop_index(op.f("ix_robots_robot_id"), table_name="robots")
    op.drop_table("robots")

    # Drop fleets table
    op.drop_index(op.f("ix_fleets_created_at"), table_name="fleets")
    op.drop_index(op.f("ix_fleets_owner_id"), table_name="fleets")
    op.drop_index(op.f("ix_fleets_fleet_id"), table_name="fleets")
    op.drop_table("fleets")
