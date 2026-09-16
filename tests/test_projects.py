"""Tests del recurso Proyectos (docs/contrato-api.md, sección Proyectos).

Estrategia de datos de fixture: todo dato de prueba se crea vía POST a
través de TestClient (la misma conexión que usa la app real), nunca
insertando directo con `db_connection`. `db_connection` abre su propia
transacción con rollback al final del test (ver tests/conftest.py) y nunca
hace commit, así que cualquier fila insertada ahí es invisible para la
conexión que la app abre por su cuenta a través de `get_engine()`. Se usa
`db_connection` solo para lecturas de verificación posteriores a un POST
(la conexión de la app sí commitea sus propios INSERT/UPDATE/DELETE).

Como las filas creadas vía API persisten realmente en la base entre tests
(no hay rollback que las limpie), ningún test se apoya en el conteo total
de filas de la tabla: solo en los campos del recurso creado por el propio
test, identificado por el `id` que devuelve la API.
"""

import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.main import app

PROJECTS_TABLE = "projects"


def _projects_table() -> sa.Table:
    metadata = sa.MetaData()
    return sa.Table(
        PROJECTS_TABLE,
        metadata,
        sa.Column("id", sa.Integer),
        sa.Column("name", sa.String),
        sa.Column("description", sa.String),
    )


# --- POST /projects ---------------------------------------------------


def test_create_project_returns_201_and_exact_schema():
    client = TestClient(app)

    response = client.post("/projects", json={"name": "Casa"})

    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {"id", "name", "description"}
    assert body["name"] == "Casa"
    assert body["description"] is None
    assert isinstance(body["id"], int)


def test_create_project_with_description_persists_it():
    client = TestClient(app)

    response = client.post(
        "/projects", json={"name": "Oficina", "description": "Proyecto de trabajo"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["description"] == "Proyecto de trabajo"


def test_create_project_without_name_returns_422():
    client = TestClient(app)

    response = client.post("/projects", json={"description": "sin nombre"})

    assert response.status_code == 422


# --- GET /projects (lista) ---------------------------------------------


def test_list_projects_returns_200_with_json_array_at_root():
    client = TestClient(app)

    response = client.get("/projects")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_projects_includes_created_project_with_exact_schema():
    client = TestClient(app)
    created = client.post("/projects", json={"name": "Jardín"}).json()

    response = client.get("/projects")

    assert response.status_code == 200
    body = response.json()
    matching = [item for item in body if item["id"] == created["id"]]
    assert len(matching) == 1
    assert matching[0] == {"id": created["id"], "name": "Jardín", "description": None}


def test_list_projects_is_ordered_by_id_ascending():
    client = TestClient(app)
    first = client.post("/projects", json={"name": "Orden A"}).json()
    second = client.post("/projects", json={"name": "Orden B"}).json()

    response = client.get("/projects")

    ids = [item["id"] for item in response.json()]
    assert ids.index(first["id"]) < ids.index(second["id"])


def test_list_projects_order_is_stable_across_identical_calls():
    client = TestClient(app)
    client.post("/projects", json={"name": "Estable"})

    first = client.get("/projects")
    second = client.get("/projects")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


# --- GET /projects/{id} -------------------------------------------------


def test_get_project_by_id_returns_200_and_exact_schema():
    client = TestClient(app)
    created = client.post("/projects", json={"name": "Detalle"}).json()

    response = client.get(f"/projects/{created['id']}")

    assert response.status_code == 200
    assert response.json() == {"id": created["id"], "name": "Detalle", "description": None}


def test_get_project_by_nonexistent_id_returns_404():
    client = TestClient(app)

    response = client.get("/projects/999999999")

    assert response.status_code == 404
    assert "detail" in response.json()


# --- PATCH /projects/{id} -----------------------------------------------


def test_patch_project_updates_only_description_and_keeps_name():
    client = TestClient(app)
    created = client.post("/projects", json={"name": "Original", "description": "vieja"}).json()

    response = client.patch(f"/projects/{created['id']}", json={"description": "nueva"})

    assert response.status_code == 200
    assert response.json() == {"id": created["id"], "name": "Original", "description": "nueva"}


def test_patch_project_updates_only_name_and_keeps_description():
    client = TestClient(app)
    created = client.post(
        "/projects", json={"name": "Antes", "description": "se mantiene"}
    ).json()

    response = client.patch(f"/projects/{created['id']}", json={"name": "Después"})

    assert response.status_code == 200
    assert response.json() == {
        "id": created["id"],
        "name": "Después",
        "description": "se mantiene",
    }


def test_patch_project_can_set_description_to_null_explicitly():
    client = TestClient(app)
    created = client.post("/projects", json={"name": "Con desc", "description": "algo"}).json()

    response = client.patch(f"/projects/{created['id']}", json={"description": None})

    assert response.status_code == 200
    assert response.json()["description"] is None


def test_patch_project_on_nonexistent_id_returns_404():
    client = TestClient(app)

    response = client.patch("/projects/999999999", json={"name": "no existe"})

    assert response.status_code == 404


def test_patch_project_returns_exact_schema():
    client = TestClient(app)
    created = client.post("/projects", json={"name": "Esquema"}).json()

    response = client.patch(f"/projects/{created['id']}", json={"description": "x"})

    assert set(response.json().keys()) == {"id", "name", "description"}


# --- DELETE /projects/{id} ------------------------------------------------
#
# El contrato exige 409 si el proyecto tiene tareas asociadas, pero el
# recurso Tareas (tabla `tasks`) todavía no existe — crearlo pertenece al
# plan de Tareas, fuera de alcance de este plan (docs/plan-proyectos.md,
# Incremento 4). La rama 409 queda sin probar por ejecución: no hay forma
# de insertar una fila de tarea real sin esa tabla. Solo se prueban aquí
# los dos casos que no dependen de `tasks` teniendo filas: borrado exitoso
# de un proyecto sin tareas, y 404 sobre un id inexistente.


def test_delete_project_on_nonexistent_id_returns_404():
    client = TestClient(app)

    response = client.delete("/projects/999999999")

    assert response.status_code == 404


def test_delete_project_without_tasks_returns_204_and_removes_it():
    client = TestClient(app)
    created = client.post("/projects", json={"name": "Para borrar"}).json()

    response = client.delete(f"/projects/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""
    follow_up = client.get(f"/projects/{created['id']}")
    assert follow_up.status_code == 404


# --- Verificación cruzada contra la base (lectura, tras commit de la app) --


def test_created_project_is_visible_directly_in_the_database(db_connection):
    client = TestClient(app)
    created = client.post("/projects", json={"name": "Verificación DB"}).json()

    projects = _projects_table()
    row = db_connection.execute(
        sa.select(projects.c.id, projects.c.name, projects.c.description).where(
            projects.c.id == created["id"]
        )
    ).one()

    assert row.name == "Verificación DB"
    assert row.description is None
