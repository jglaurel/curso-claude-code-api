import unicodedata

import sqlalchemy as sa
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

from app.db import get_engine

# docs/contrato-api.md, sección "Normalización de texto": categorías Unicode
# que no cuentan como carácter visible.
_INVISIBLE_CATEGORIES = {"Cc", "Cf", "Zl", "Zp", "Zs"}

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

_tasks_table = sa.table(
    "tasks",
    sa.column("id", sa.Integer),
    sa.column("title", sa.String),
    sa.column("description", sa.String),
    sa.column("project_id", sa.Integer),
    sa.column("state_id", sa.Integer),
)


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


def _normalize_title(value: str) -> str:
    stripped = value.strip()
    has_visible_char = any(
        unicodedata.category(char) not in _INVISIBLE_CATEGORIES for char in stripped
    )
    if not has_visible_char:
        raise ValueError("el título no puede estar vacío")
    return stripped


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    project_id: int
    state_id: int

    @field_validator("title")
    @classmethod
    def _validate_title(cls, value: str) -> str:
        return _normalize_title(value)


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


def _project_has_tasks(connection, project_id: int) -> bool:
    query = sa.select(sa.exists().where(_tasks_table.c.project_id == project_id))
    return bool(connection.execute(query).scalar())


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


@app.patch("/projects/{project_id}")
def update_project(project_id: int, payload: ProjectUpdate) -> dict[str, object]:
    updates = payload.model_dump(exclude_unset=True)
    with get_engine().connect() as connection:
        if updates:
            update_stmt = (
                sa.update(_projects_table)
                .where(_projects_table.c.id == project_id)
                .values(**updates)
                .returning(
                    _projects_table.c.id, _projects_table.c.name, _projects_table.c.description
                )
            )
            row = connection.execute(update_stmt).one_or_none()
            connection.commit()
        else:
            query = sa.select(
                _projects_table.c.id, _projects_table.c.name, _projects_table.c.description
            ).where(_projects_table.c.id == project_id)
            row = connection.execute(query).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="proyecto no encontrado")
    return _project_to_dict(row)


@app.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: int) -> None:
    with get_engine().connect() as connection:
        exists_query = sa.select(sa.exists().where(_projects_table.c.id == project_id))
        if not connection.execute(exists_query).scalar():
            raise HTTPException(status_code=404, detail="proyecto no encontrado")

        if _project_has_tasks(connection, project_id):
            raise HTTPException(status_code=409, detail="el proyecto tiene tareas asociadas")

        connection.execute(sa.delete(_projects_table).where(_projects_table.c.id == project_id))
        connection.commit()


def _task_to_dict(row) -> dict[str, object]:
    return {
        "id": row.id,
        "title": row.title,
        "description": row.description,
        "project_id": row.project_id,
        "state_id": row.state_id,
    }


def _project_exists(connection, project_id: int) -> bool:
    query = sa.select(sa.exists().where(_projects_table.c.id == project_id))
    return bool(connection.execute(query).scalar())


def _state_exists(connection, state_id: int) -> bool:
    query = sa.select(sa.exists().where(_states_table.c.id == state_id))
    return bool(connection.execute(query).scalar())


@app.post("/tasks", status_code=201)
def create_task(payload: TaskCreate) -> dict[str, object]:
    with get_engine().connect() as connection:
        if not _project_exists(connection, payload.project_id):
            raise HTTPException(status_code=422, detail="el proyecto no existe")
        if not _state_exists(connection, payload.state_id):
            raise HTTPException(status_code=422, detail="el estado no existe")

        insert_stmt = (
            sa.insert(_tasks_table)
            .values(
                title=payload.title,
                description=payload.description,
                project_id=payload.project_id,
                state_id=payload.state_id,
            )
            .returning(
                _tasks_table.c.id,
                _tasks_table.c.title,
                _tasks_table.c.description,
                _tasks_table.c.project_id,
                _tasks_table.c.state_id,
            )
        )
        row = connection.execute(insert_stmt).one()
        connection.commit()
    return _task_to_dict(row)


@app.get("/tasks")
def list_tasks(
    project_id: int | None = None, state_id: int | None = None
) -> list[dict[str, object]]:
    query = sa.select(
        _tasks_table.c.id,
        _tasks_table.c.title,
        _tasks_table.c.description,
        _tasks_table.c.project_id,
        _tasks_table.c.state_id,
    )
    if project_id is not None:
        query = query.where(_tasks_table.c.project_id == project_id)
    if state_id is not None:
        query = query.where(_tasks_table.c.state_id == state_id)
    query = query.order_by(_tasks_table.c.id)
    with get_engine().connect() as connection:
        rows = connection.execute(query).all()
    return [_task_to_dict(row) for row in rows]


@app.get("/tasks/{task_id}")
def get_task(task_id: int) -> dict[str, object]:
    query = sa.select(
        _tasks_table.c.id,
        _tasks_table.c.title,
        _tasks_table.c.description,
        _tasks_table.c.project_id,
        _tasks_table.c.state_id,
    ).where(_tasks_table.c.id == task_id)
    with get_engine().connect() as connection:
        row = connection.execute(query).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="tarea no encontrada")
    return _task_to_dict(row)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int) -> None:
    with get_engine().connect() as connection:
        exists_query = sa.select(sa.exists().where(_tasks_table.c.id == task_id))
        if not connection.execute(exists_query).scalar():
            raise HTTPException(status_code=404, detail="tarea no encontrada")

        connection.execute(sa.delete(_tasks_table).where(_tasks_table.c.id == task_id))
        connection.commit()
