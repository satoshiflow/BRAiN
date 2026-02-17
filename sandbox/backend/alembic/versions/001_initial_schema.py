"""Initial schema - Placeholder for BRAiN v0.3.0

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-12-19 00:00:00.000000

This is a placeholder migration created during Phase 1 setup.
Real schema migrations will be generated when database models are implemented.

To create new migrations:
    alembic revision --autogenerate -m "description"

To apply migrations:
    alembic upgrade head

To rollback:
    alembic downgrade -1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade to initial schema.

    Currently empty - models will be added in future migrations.
    """
    # TODO: Create tables for:
    # - DNA snapshots (app.modules.dna)
    # - Missions (modules/missions - legacy)
    # - Agent metadata
    # - KARMA scores
    # - Threats
    # - Policies
    pass


def downgrade() -> None:
    """
    Downgrade from initial schema.

    Currently empty.
    """
    pass
