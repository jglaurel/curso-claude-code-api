"""create projects table

Revision ID: ba948a7595c2
Revises: 501de659f4ac
Create Date: 2026-09-16 11:28:56.570954

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ba948a7595c2'
down_revision: Union[str, Sequence[str], None] = '501de659f4ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROJECTS_TABLE = "projects"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        PROJECTS_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table(PROJECTS_TABLE)
