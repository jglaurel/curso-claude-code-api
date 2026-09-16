"""create tasks table

Revision ID: 49ab9a5073b5
Revises: ba948a7595c2
Create Date: 2026-09-16 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '49ab9a5073b5'
down_revision: Union[str, Sequence[str], None] = 'ba948a7595c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TASKS_TABLE = "tasks"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        TASKS_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("state_id", sa.Integer(), sa.ForeignKey("states.id"), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table(TASKS_TABLE)
