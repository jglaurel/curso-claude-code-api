# Plan: conexión de la API a PostgreSQL

Plan de referencia. Úsalo solo si no tienes el que acordaste en la sesión 3.

Cubre **Salud** y **Estados**. Cada incremento es un commit que se confirma
solo; al terminar uno se para y se espera aprobación antes del siguiente.

Fuentes: `docs/contrato-api.md` (secciones Salud y Estados),
`docs/decisiones-ingenieria.md`, `CLAUDE.md`.

## Fuera de alcance

Proyectos, tareas, filtros, `due_at`, skills, hooks y verificación automatizada.

## Estado del repositorio al planificar

- `app/main.py`: un solo endpoint, `GET /health` que responde `200` con
  `{"status": "ok"}`.
- Sin ORM, sin driver de PostgreSQL, sin Alembic y sin código que lea
  configuración de conexión.
- `tests/test_health.py`: un test async, app en memoria.
- `pyproject.toml`: dependencias `fastapi` y `uvicorn`; de desarrollo `pytest`,
  `pytest-asyncio`, `httpx` y `ruff`. Python 3.12.
- `compose.yaml`: servicio `db` con PostgreSQL 18-alpine y healthcheck.
- `.env.example`: solo variables `POSTGRES_*`. No hay `DATABASE_URL`.
- `docs/decisiones-ingenieria.md` exige migraciones probadas en los dos
  sentidos, tests de persistencia contra PostgreSQL y nunca contra SQLite, y
  que toda capacidad nueva empiece por un test que falla.

## Decisión tomada: driver y capa de acceso

Acceso **síncrono** con SQLAlchemy 2.x y el driver `psycopg` (v3).

Encaja con lo que ya tiene el repositorio: `pyproject.toml` declara
`psycopg[binary]` como dependencia, `app/db.py` expone un `create_engine()`
cacheado (síncrono, no un motor async), y este enfoque simplifica las
migraciones y las conexiones directas desde FastAPI sin el overhead
asíncrono que no hace falta aquí.

## Incrementos

### Incremento 1 — Dependencias y configuración de conexión

- Añadir a `pyproject.toml`: `sqlalchemy[asyncio]`, `asyncpg` y `alembic`.
- Módulo `app/db.py` que crea el motor y la fábrica de sesiones leyendo
  `DATABASE_URL` del entorno.
- Añadir `DATABASE_URL` a `.env.example`, derivada de los `POSTGRES_*` que ya
  están.
- **Comprobación:** las dependencias resuelven; el módulo se importa sin
  conectar; la suite y el linter siguen en verde.

### Incremento 2 — Alembic inicializado, sin cambios de esquema

- Inicializar Alembic, ajustar su configuración para usar `DATABASE_URL` y el
  metadata de la app, y crear una revisión inicial sin operaciones de esquema.
- Documentar en `README.md` cómo se sube y se baja una migración.
- **Comprobación:** con la base levantada, subir crea la tabla de versiones y
  bajar la revierte. Las dos direcciones probadas.

### Incremento 3 — Migración de la tabla `states` con seed idempotente

- Migración que crea la tabla del catálogo con identificador, código y campo de
  orden, y siembra los cuatro estados del contrato al subir. Al bajar, la
  elimina.
- El seed es **idempotente**: aplicarlo dos veces deja el mismo resultado que
  aplicarlo una, sin duplicar filas.
- **Comprobación:** un test contra PostgreSQL que verifica que tras subir hay
  exactamente cuatro estados con los códigos del contrato, que repetir el seed
  no cambia el conteo, y que al bajar la tabla desaparece.

### Incremento 4 — Endpoint `GET /states`

- Test que falla primero: la respuesta es `200`, una lista JSON en la raíz, cada
  elemento con exactamente los campos que el contrato declara, y el orden
  estable.
- Después, la ruta que consulta la tabla y serializa con un esquema de salida
  estricto, sin campos de más.
- **Comprobación:** el test nuevo pasa, el de salud sigue pasando, el linter
  está en verde y dos llamadas idénticas devuelven el mismo orden.
