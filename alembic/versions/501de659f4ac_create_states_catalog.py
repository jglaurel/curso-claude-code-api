"""create states catalog

Revision ID: 501de659f4ac
Revises:
Create Date: 2026-09-08 15:37:21.601014

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '501de659f4ac'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATES_TABLE = "states"

# Catálogo fijo (docs/contrato-api.md, sección Estados). sort_order fija el
# orden de GET /states; el orden de esta lista es el orden del contrato.
STATE_SEED = [
    {"code": "PENDIENTE", "sort_order": 1},
    {"code": "EN_CURSO", "sort_order": 2},
    {"code": "BLOQUEADA", "sort_order": 3},
    {"code": "HECHA", "sort_order": 4},
]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        STATES_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.UniqueConstraint("code", name="uq_states_code"),
    )

    states = sa.table(
        STATES_TABLE,
        sa.column("code", sa.String),
        sa.column("sort_order", sa.Integer),
    )
    # ON CONFLICT DO NOTHING sobre `code`: el seed queda idempotente aunque
    # esta migración se ejecute más de una vez sobre la misma base.
    insert_stmt = pg_insert(states).values(STATE_SEED)
    op.execute(insert_stmt.on_conflict_do_nothing(index_elements=["code"]))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table(STATES_TABLE)
