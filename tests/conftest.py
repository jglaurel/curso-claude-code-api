import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine

from app.config import get_settings


@pytest.fixture(scope="session")
def db_engine() -> Engine:
    engine = create_engine(get_settings().database_url)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_connection(db_engine: Engine) -> Connection:
    """Conexión con transacción propia, revertida al terminar el test.

    Aísla los tests de persistencia entre sí sin dejar residuos en la base
    real: incluso si un test escribe (p. ej. para probar idempotencia del
    seed), el rollback deja la base como estaba.
    """
    with db_engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()
