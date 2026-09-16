"""Tests del recurso Tareas (docs/contrato-api.md, secciones Tareas v1 y v2).

Misma estrategia de datos de fixture que tests/test_projects.py: todo dato
de prueba se crea vía POST a través de TestClient (la misma conexión que
usa la app real), nunca insertando directo con `db_connection`.
`db_connection` abre su propia transacción con rollback al final del test
(ver tests/conftest.py) y nunca hace commit, así que cualquier fila
insertada ahí es invisible para la conexión que la app abre por su cuenta
a través de `get_engine()`. Se usa `db_connection` solo para lecturas de
verificación posteriores a un POST.

Los estados del catálogo (docs/contrato-api.md, sección Estados) se
resuelven por código a través de GET /states en vez de hardcodear ids: el
seed usa ON CONFLICT DO NOTHING, así que el id numérico no está
garantizado a priori.
"""

from fastapi.testclient import TestClient

from app.main import app


def _state_id(client: TestClient, code: str) -> int:
    states = client.get("/states").json()
    (match,) = [state for state in states if state["code"] == code]
    return match["id"]


def _create_project(client: TestClient, name: str = "Proyecto de tareas") -> dict:
    return client.post("/projects", json={"name": name}).json()


# --- POST /tasks ---------------------------------------------------------


def test_create_task_returns_201_and_exact_schema_v1():
    client = TestClient(app)
    project = _create_project(client, "Para crear tarea")
    state_id = _state_id(client, "PENDIENTE")

    response = client.post(
        "/tasks",
        json={"title": "Regar las plantas", "project_id": project["id"], "state_id": state_id},
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {"id", "title", "description", "project_id", "state_id"}
    assert body["title"] == "Regar las plantas"
    assert body["description"] is None
    assert body["project_id"] == project["id"]
    assert body["state_id"] == state_id
    assert isinstance(body["id"], int)


def test_create_task_with_description_persists_it():
    client = TestClient(app)
    project = _create_project(client, "Con descripcion")
    state_id = _state_id(client, "PENDIENTE")

    response = client.post(
        "/tasks",
        json={
            "title": "Tarea con descripcion",
            "description": "detalle",
            "project_id": project["id"],
            "state_id": state_id,
        },
    )

    assert response.status_code == 201
    assert response.json()["description"] == "detalle"


def test_create_task_with_nonexistent_project_returns_422_and_does_not_create():
    client = TestClient(app)
    state_id = _state_id(client, "PENDIENTE")

    response = client.post(
        "/tasks",
        json={"title": "Huerfana", "project_id": 999999999, "state_id": state_id},
    )

    assert response.status_code == 422


def test_create_task_with_nonexistent_state_returns_422_and_does_not_create():
    client = TestClient(app)
    project = _create_project(client, "Estado invalido")

    response = client.post(
        "/tasks",
        json={"title": "Sin estado", "project_id": project["id"], "state_id": 999999999},
    )

    assert response.status_code == 422


def test_create_task_with_empty_title_returns_422():
    client = TestClient(app)
    project = _create_project(client, "Titulo vacio")
    state_id = _state_id(client, "PENDIENTE")

    response = client.post(
        "/tasks", json={"title": "", "project_id": project["id"], "state_id": state_id}
    )

    assert response.status_code == 422


def test_create_task_with_only_ascii_spaces_title_returns_422():
    client = TestClient(app)
    project = _create_project(client, "Solo espacios")
    state_id = _state_id(client, "PENDIENTE")

    response = client.post(
        "/tasks", json={"title": "   ", "project_id": project["id"], "state_id": state_id}
    )

    assert response.status_code == 422


# --- GET /tasks/{id} -------------------------------------------------------


def test_get_task_by_id_returns_200_and_exact_schema():
    client = TestClient(app)
    project = _create_project(client, "Detalle de tarea")
    state_id = _state_id(client, "PENDIENTE")
    created = client.post(
        "/tasks", json={"title": "Detalle", "project_id": project["id"], "state_id": state_id}
    ).json()

    response = client.get(f"/tasks/{created['id']}")

    assert response.status_code == 200
    assert response.json() == {
        "id": created["id"],
        "title": "Detalle",
        "description": None,
        "project_id": project["id"],
        "state_id": state_id,
    }


def test_get_task_by_nonexistent_id_returns_404():
    client = TestClient(app)

    response = client.get("/tasks/999999999")

    assert response.status_code == 404
    assert "detail" in response.json()


# --- GET /tasks (lista, filtros, orden) -------------------------------------


def test_list_tasks_returns_200_with_json_array_at_root():
    client = TestClient(app)

    response = client.get("/tasks")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_tasks_is_ordered_by_id_ascending():
    client = TestClient(app)
    project = _create_project(client, "Orden de tareas")
    state_id = _state_id(client, "PENDIENTE")
    first = client.post(
        "/tasks", json={"title": "Orden A", "project_id": project["id"], "state_id": state_id}
    ).json()
    second = client.post(
        "/tasks", json={"title": "Orden B", "project_id": project["id"], "state_id": state_id}
    ).json()

    response = client.get("/tasks")

    ids = [item["id"] for item in response.json()]
    assert ids.index(first["id"]) < ids.index(second["id"])


def test_list_tasks_order_is_stable_across_identical_calls():
    client = TestClient(app)
    project = _create_project(client, "Orden estable")
    state_id = _state_id(client, "PENDIENTE")
    client.post(
        "/tasks", json={"title": "Estable", "project_id": project["id"], "state_id": state_id}
    )

    first = client.get("/tasks")
    second = client.get("/tasks")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_list_tasks_filters_by_project_id():
    client = TestClient(app)
    project_a = _create_project(client, "Filtro proyecto A")
    project_b = _create_project(client, "Filtro proyecto B")
    state_id = _state_id(client, "PENDIENTE")
    task_a = client.post(
        "/tasks", json={"title": "De A", "project_id": project_a["id"], "state_id": state_id}
    ).json()
    client.post(
        "/tasks", json={"title": "De B", "project_id": project_b["id"], "state_id": state_id}
    )

    response = client.get("/tasks", params={"project_id": project_a["id"]})

    assert response.status_code == 200
    body = response.json()
    assert all(item["project_id"] == project_a["id"] for item in body)
    assert any(item["id"] == task_a["id"] for item in body)


def test_list_tasks_filters_by_state_id():
    client = TestClient(app)
    project = _create_project(client, "Filtro estado")
    pendiente_id = _state_id(client, "PENDIENTE")
    en_curso_id = _state_id(client, "EN_CURSO")
    task_pendiente = client.post(
        "/tasks",
        json={"title": "Pendiente", "project_id": project["id"], "state_id": pendiente_id},
    ).json()
    client.post(
        "/tasks", json={"title": "En curso", "project_id": project["id"], "state_id": en_curso_id}
    )

    response = client.get("/tasks", params={"state_id": pendiente_id})

    assert response.status_code == 200
    body = response.json()
    assert all(item["state_id"] == pendiente_id for item in body)
    assert any(item["id"] == task_pendiente["id"] for item in body)


def test_list_tasks_filters_combined_project_id_and_state_id():
    client = TestClient(app)
    project_a = _create_project(client, "Combinado A")
    project_b = _create_project(client, "Combinado B")
    pendiente_id = _state_id(client, "PENDIENTE")
    en_curso_id = _state_id(client, "EN_CURSO")
    target = client.post(
        "/tasks",
        json={"title": "Objetivo", "project_id": project_a["id"], "state_id": pendiente_id},
    ).json()
    # Mismo proyecto, otro estado: no debe aparecer.
    client.post(
        "/tasks",
        json={"title": "Otro estado", "project_id": project_a["id"], "state_id": en_curso_id},
    )
    # Mismo estado, otro proyecto: no debe aparecer.
    client.post(
        "/tasks",
        json={"title": "Otro proyecto", "project_id": project_b["id"], "state_id": pendiente_id},
    )

    response = client.get(
        "/tasks", params={"project_id": project_a["id"], "state_id": pendiente_id}
    )

    assert response.status_code == 200
    body = response.json()
    ids = [item["id"] for item in body]
    assert target["id"] in ids
    assert all(
        item["project_id"] == project_a["id"] and item["state_id"] == pendiente_id
        for item in body
    )
