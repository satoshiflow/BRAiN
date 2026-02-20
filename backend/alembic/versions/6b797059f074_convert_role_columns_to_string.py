"""Convert role columns from enum to string

Revision ID: 6b797059f074
Revises: 6a797059f073
Create Date: 2026-02-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b797059f074'
down_revision: Union[str, None] = '6a797059f073'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert users.role from enum to string
    op.alter_column('users', 'role',
                    existing_type=sa.Enum('admin', 'operator', 'viewer', name='userrole'),
                    type_=sa.String(length=50),
                    existing_nullable=False,
                    postgresql_using='role::text')
    
    # Convert invitations.role from enum to string  
    op.alter_column('invitations', 'role',
                    existing_type=sa.Enum('admin', 'operator', 'viewer', name='userrole'),
                    type_=sa.String(length=50),
                    existing_nullable=False,
                    postgresql_using='role::text')
    
    # Drop the enum type (optional - keep for compatibility)
    # op.execute('DROP TYPE IF EXISTS userrole')


def downgrade() -> None:
    # Recreate enum type if needed
    # op.execute("CREATE TYPE userrole AS ENUM ('admin', 'operator', 'viewer')")
    
    # Convert back to enum
    op.alter_column('users', 'role',
                    existing_type=sa.String(length=50),
                    type_=sa.Enum('admin', 'operator', 'viewer', name='userrole'),
                    existing_nullable=False,
                    postgresql_using='role::userrole')
    
    op.alter_column('invitations', 'role',
                    existing_type=sa.String(length=50),
                    type_=sa.Enum('admin', 'operator', 'viewer', name='userrole'),
                    existing_nullable=False,
                    postgresql_using='role::userrole')
