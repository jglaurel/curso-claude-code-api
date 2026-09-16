import sqlalchemy as sa
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.db import get_engine

app = FastAPI(title="TaskFlow API")

_states_table = sa.table(
    "states",
    sa.column("id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("sort_order", sa.Integer),
)

_projects_table = sa.table(
    "projects",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("description", sa.String),
)


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


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


def _project_to_dict(row) -> dict[str, object]:
    return {"id": row.id, "name": row.name, "description": row.description}


@app.post("/projects", status_code=201)
def create_project(payload: ProjectCreate) -> dict[str, object]:
    insert_stmt = (
        sa.insert(_projects_table)
        .values(name=payload.name, description=payload.description)
        .returning(_projects_table.c.id, _projects_table.c.name, _projects_table.c.description)
    )
    with get_engine().connect() as connection:
        row = connection.execute(insert_stmt).one()
        connection.commit()
    return _project_to_dict(row)


@app.get("/projects")
def list_projects() -> list[dict[str, object]]:
    query = sa.select(
        _projects_table.c.id, _projects_table.c.name, _projects_table.c.description
    ).order_by(_projects_table.c.id)
    with get_engine().connect() as connection:
        rows = connection.execute(query).all()
    return [_project_to_dict(row) for row in rows]


@app.get("/projects/{project_id}")
def get_project(project_id: int) -> dict[str, object]:
    query = sa.select(
        _projects_table.c.id, _projects_table.c.name, _projects_table.c.description
    ).where(_projects_table.c.id == project_id)
    with get_engine().connect() as connection:
        row = connection.execute(query).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="proyecto no encontrado")
    return _project_to_dict(row)
