"""Tests del catálogo de estados (docs/contrato-api.md, sección Estados).

Cubre dos capas distintas:

- Persistencia: el catálogo fijo existe tras migrar y reaplicar el seed no
  lo duplica. Corre contra PostgreSQL real, sin pasar por la API.
- API: `GET /states` responde 200 con el esquema exacto y orden estable.
  El endpoint todavía no existe, así que estos casos fallan por aserción
  (404 no es 200), no por error de importación.
"""

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.main import app

STATES_TABLE = "states"
EXPECTED_CODES_IN_ORDER = ["PENDIENTE", "EN_CURSO", "BLOQUEADA", "HECHA"]

_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "alembic" / "versions"


def _load_states_migration():
    """Carga el módulo de la migración que crea y siembra `states`.

    Se importa por ruta (no con `import`) porque el nombre del archivo
    empieza con el revision id de Alembic y no es un identificador válido
    de Python. Se reutiliza `STATE_SEED` de ahí para no duplicar el
    catálogo a mano en el test y arriesgar que diverja del contrato.
    """
    (migration_path,) = _MIGRATIONS_DIR.glob("*_create_states_catalog.py")
    spec = importlib.util.spec_from_file_location("states_catalog_migration", migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _states_table() -> sa.Table:
    metadata = sa.MetaData()
    return sa.Table(
        STATES_TABLE,
        metadata,
        sa.Column("id", sa.Integer),
        sa.Column("code", sa.String),
        sa.Column("sort_order", sa.Integer),
    )


def _fetch_states(connection):
    states = _states_table()
    rows = connection.execute(
        sa.select(states.c.id, states.c.code).order_by(states.c.sort_order, states.c.id)
    ).all()
    return [{"id": row.id, "code": row.code} for row in rows]


# --- Persistencia ------------------------------------------------------


def test_states_catalog_has_exactly_the_four_contract_states(db_connection):
    states = _states_table()

    rows = db_connection.execute(
        sa.select(states.c.code).order_by(states.c.sort_order, states.c.id)
    ).all()
    codes = [row.code for row in rows]

    assert codes == EXPECTED_CODES_IN_ORDER


def test_states_catalog_codes_are_unique(db_connection):
    states = _states_table()

    total = db_connection.execute(sa.select(sa.func.count()).select_from(states)).scalar_one()
    distinct_total = db_connection.execute(
        sa.select(sa.func.count(sa.distinct(states.c.code)))
    ).scalar_one()

    assert total == 4
    assert total == distinct_total


def test_reapplying_the_states_seed_does_not_duplicate_rows(db_connection):
    migration = _load_states_migration()
    states = _states_table()

    insert_stmt = pg_insert(states).values(migration.STATE_SEED)
    insert_stmt = insert_stmt.on_conflict_do_nothing(index_elements=["code"])

    # Reaplica el seed dentro de la misma transacción de test (se revierte
    # al final): si no fuera idempotente, esto duplicaría filas.
    db_connection.execute(insert_stmt)
    db_connection.execute(insert_stmt)

    total = db_connection.execute(sa.select(sa.func.count()).select_from(states)).scalar_one()
    assert total == 4


# --- API -----------------------------------------------------------------


def test_get_states_returns_200():
    client = TestClient(app)

    response = client.get("/states")

    assert response.status_code == 200


def test_get_states_returns_exact_schema_in_contract_order(db_connection):
    client = TestClient(app)

    response = client.get("/states")

    assert response.status_code == 200
    body = response.json()
    assert body == _fetch_states(db_connection)
    assert [state["code"] for state in body] == EXPECTED_CODES_IN_ORDER


def test_get_states_order_is_stable_across_identical_calls():
    client = TestClient(app)

    first = client.get("/states")
    second = client.get("/states")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
