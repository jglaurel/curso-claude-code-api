import sqlalchemy as sa
from fastapi import FastAPI

from app.db import get_engine

app = FastAPI(title="TaskFlow API")

_states_table = sa.table(
    "states",
    sa.column("id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("sort_order", sa.Integer),
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/states")
def list_states() -> list[dict[str, object]]:
    query = sa.select(_states_table.c.id, _states_table.c.code).order_by(
        _states_table.c.sort_order, _states_table.c.id
    )
    with get_engine().connect() as connection:
        rows = connection.execute(query).all()
    return [{"id": row.id, "code": row.code} for row in rows]
