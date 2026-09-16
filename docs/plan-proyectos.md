# Plan: recurso Proyectos

Cubre la sección **Proyectos** de `docs/contrato-api.md`: CRUD completo de
`/projects`, con el `409` de borrado bloqueado por tareas ya declarado en el
contrato (aunque las tareas todavía no existen como recurso en el código).

Cada incremento es un commit que se confirma solo; al terminar uno se para y
se espera aprobación antes del siguiente.

## Fuentes consultadas

- `docs/contrato-api.md` — sección Proyectos (campos, rutas, códigos de
  estado, orden de listas, esquema de respuesta exacto, matriz mínima de
  tests) y sección "Normalización de texto" (se aplica explícitamente solo a
  `title` de tarea).
- `docs/decisiones-ingenieria.md` — persistencia solo contra PostgreSQL,
  migraciones de Alembic escritas a mano con `upgrade`/`downgrade` probados
  en ambos sentidos, disciplina de tests (capacidad nueva empieza con un caso
  que falla).
- `README.md` — comandos canónicos (`uv sync --locked`, `uv run pytest -q`,
  `uv run ruff check .`, migraciones con `alembic upgrade head` /
  `downgrade -1` / `downgrade base`).
- `CLAUDE.md` — guía operativa vigente.
- `docs/plan-persistencia.md` — plan previo del mismo repositorio: fija el
  patrón de incrementos que ya se ejecutó para Salud y Estados. Este plan no
  repite Salud ni Estados; los da por hechos y sigue el mismo patrón para
  Proyectos.
- Estado real del repositorio (`git status`, `git log --oneline -15`, y
  lectura directa de `app/`, `tests/`, `alembic/`, `pyproject.toml`).

## Estado del repositorio al planificar

- `app/main.py`: dos endpoints, `GET /health` y `GET /states`. `GET /states`
  consulta la tabla `states` con SQLAlchemy Core (`sa.table`, sin ORM) a
  través de `get_engine()` (`app/db.py`), un `create_engine()` síncrono
  cacheado con `lru_cache` que usa el driver `psycopg` v3
  (`postgresql+psycopg://...`). No hay ningún endpoint de escritura
  implementado todavía en el repositorio: `GET /states` es de solo lectura.
- `app/config.py`: `Settings` como `dataclass` congelada, construida a partir
  de variables `POSTGRES_*` de entorno; no expone nada específico de
  proyectos.
- `alembic/env.py`: `target_metadata = None` — el proyecto **no usa
  autogenerate**; las migraciones se escriben a mano. La URL de conexión sale
  de `app.config.get_settings()`, no de `alembic.ini`.
- `alembic/versions/501de659f4ac_create_states_catalog.py`: única migración
  existente. Patrón de referencia para la nueva: `op.create_table` en
  `upgrade()`, `op.drop_table` en `downgrade()`, tabla intermedia con
  `sa.table()` para los `insert`/`select` en lugar de un modelo ORM.
- `tests/conftest.py`: fixtures `db_engine` (scope sesión, contra
  PostgreSQL real vía `get_settings().database_url`) y `db_connection`
  (transacción por test, con rollback al terminar — aísla tests de
  persistencia sin dejar residuos). Reutilizables tal cual para los tests de
  proyectos.
- `tests/test_states.py` y `tests/test_health.py`: usan `TestClient(app)`
  directo, sin fixture de cliente compartida. Se sigue el mismo patrón.
- `pyproject.toml`: dependencias ya declaradas — `fastapi`, `sqlalchemy`,
  `psycopg[binary]`, `alembic`. **No hace falta añadir ninguna dependencia
  nueva** para implementar Proyectos: no hay `pydantic` declarado de forma
  explícita porque `fastapi` ya lo trae como dependencia transitiva, y los
  esquemas de entrada/salida de `GET /states` ya se construyen con
  diccionarios simples, no con modelos Pydantic — este plan tampoco necesita
  introducir Pydantic para cumplir el contrato: son igualmente válidos los
  diccionarios, si el incremento correspondiente los valida al mismo nivel
  que exige el contrato.
- No existe ninguna tabla, migración, ruta ni test relacionado con
  `projects` en el repositorio. Se parte de cero para este recurso.
- No hay ningún `docs/plan-proyectos.md` previo con el que este documento
  pudiera entrar en conflicto.

## Decisión resuelta antes de planificar

El contrato no aclara si `name` de proyecto está sujeto a la misma regla de
"Normalización de texto" que `title` de tarea (esa sección del contrato dice
explícitamente que aplica a `title` de tarea; no menciona `name` de
proyecto). Se preguntó y se decidió: **`name` de proyecto no lleva la
normalización Unicode de `title`**; solo se valida como string no vacío, con
la validación por defecto que ya aplica el framework (rechazo de ausencia o
tipo incorrecto). No hay `422` especial por espacios en blanco o caracteres
invisibles en `name` de proyecto.

## Fuera de alcance

- Tareas como recurso (`POST/GET/PATCH/DELETE /tasks`, filtros, `due_at`) y
  cualquier tabla `tasks`, aunque sea mínima: pertenecen a un incremento
  posterior. Este plan **sí** implementa la lógica del `409` de `DELETE
  /projects/{id}` cuando el proyecto tiene tareas, pero esa rama queda sin
  probar por ejecución hasta que exista la tabla `tasks` (ver limitación
  declarada en el Incremento 4). No se crea ninguna tabla ni endpoint de
  tareas aquí.
- Autenticación, autorización o cualquier control de acceso a `/projects`.
- Paginación de `GET /projects`: el contrato solo exige orden determinista
  por `id` ascendente, no pide paginar.
- Cualquier campo de proyecto más allá de `id`, `name`, `description`: el
  contrato fija esos como "ni más ni menos".
- Cambios al contrato: si durante la implementación aparece una ambigüedad
  nueva no cubierta por este plan, se resuelve actualizando primero
  `docs/contrato-api.md` en un commit separado, según exige `CLAUDE.md`.
- Documentación de arranque/migraciones en `README.md`: ya cubre el flujo de
  Alembic genérico (`upgrade head`, `downgrade -1`, `downgrade base`); no
  hace falta un comando nuevo específico para proyectos.

## Incrementos

### Incremento 1 — Migración: tabla `projects`

- Nueva migración de Alembic (`down_revision` apuntando a
  `501de659f4ac`) que crea la tabla `projects` con:
  - `id`: entero, clave primaria autogenerada.
  - `name`: string, `nullable=False`.
  - `description`: string, `nullable=True`.
- Sin seed: a diferencia de `states`, `projects` no es un catálogo fijo —
  las filas las crea la API.
- `downgrade()` elimina la tabla.
- **Comprobación ejecutable:**
  ```
  docker compose up -d
  uv run alembic upgrade head
  uv run alembic downgrade -1
  uv run alembic upgrade head
  ```
  Sube sin error, baja sin error (la tabla `projects` desaparece), y volver
  a subir la recrea limpia.

### Incremento 2 — `POST /projects` y `GET /projects` (lista y por id)

- Test primero (falla por ausencia de la capacidad, no por error de
  importación): `POST /projects` con `name` válido responde `201` con el
  recurso creado y esquema exacto (`id`, `name`, `description` — con
  `description` ausente serializado como `null`, no omitido); `POST` sin
  `name` responde `422`; `GET /projects` responde `200` con lista JSON en la
  raíz, ordenada por `id` ascendente; `GET /projects/{id}` responde `200`
  para un proyecto existente y `404` para uno inexistente.
- Implementación: rutas en `app/main.py` siguiendo el patrón de `GET
  /states` (SQLAlchemy Core vía `get_engine()`, sin ORM, tabla intermedia
  con `sa.table()` o `sa.Table()` declarada para `projects`). Inserción con
  `INSERT ... RETURNING` o `insert()` + `select()` posterior, consistente con
  el estilo síncrono ya usado.
- **Comprobación ejecutable:**
  ```
  uv run pytest -q tests/test_projects.py
  uv run pytest -q
  uv run ruff check .
  ```
  Los tests nuevos pasan, la suite completa sigue en verde, el linter no
  reporta hallazgos.

### Incremento 3 — `PATCH /projects/{id}`

- Test primero: `PATCH` con solo `description` deja `name` intacto (y
  viceversa); `PATCH` sobre un `id` inexistente responde `404`; la respuesta
  tiene el esquema exacto del contrato.
- Implementación: actualización parcial (solo los campos presentes en el
  cuerpo de la petición se modifican) siguiendo el mismo acceso a datos que
  el resto de rutas.
- **Comprobación ejecutable:**
  ```
  uv run pytest -q tests/test_projects.py
  uv run ruff check .
  ```
  Los casos de `PATCH` (parcial y `404`) pasan; el resto de
  `test_projects.py` sigue en verde.

### Incremento 4 — `DELETE /projects/{id}`: `204` sin tareas, `409` con tareas

- El contrato exige `409` si el proyecto tiene tareas y no permite borrado en
  cascada implícito. El recurso Tareas todavía no existe en el código (fuera
  de alcance de este plan), así que este incremento **no crea ninguna tabla
  `tasks`**, ni siquiera mínima: crear esquema de Tareas —aunque sea
  parcial— pertenece al plan de Tareas, no al de Proyectos.
- Implementación: la ruta de borrado incluye la comprobación lógica de
  tareas asociadas (p. ej. `SELECT EXISTS (... FROM tasks WHERE project_id =
  :id)` o equivalente) antes de ejecutar el `DELETE`, y responde `409` sin
  borrar si la comprobación encuentra alguna. Esta comprobación referencia
  una tabla `tasks` que aún no existe en el esquema de la base — el código
  queda escrito contra el nombre y la columna (`tasks.project_id`) que el
  contrato ya fija para Tareas, anticipando el esquema, pero **no se ejecuta
  contra una base real dentro de este plan** (ver limitación abajo).
- Test primero, solo para los dos casos que sí se pueden probar sin la tabla
  `tasks`: `DELETE /projects/{id}` sobre un proyecto sin tareas responde
  `204` sin cuerpo y el proyecto deja de existir (`GET` posterior da `404`);
  sobre un `id` inexistente responde `404`.
- **Limitación declarada explícitamente:** la rama `409` (proyecto con
  tareas) **queda sin probar** en este incremento. No existe una tabla
  `tasks` contra la que insertar una fila asociada, así que no hay forma de
  ejercitar esa rama con un test real sin invadir el alcance de Tareas. La
  comprobación lógica queda implementada y revisable por lectura de código,
  pero no verificada por ejecución. Cuando el plan de Tareas cree la tabla
  `tasks`, ese plan debe incluir —como parte de su propio alcance, no del de
  Proyectos— el test que ejercita `DELETE /projects/{id}` devolviendo `409`
  con una tarea real asociada, cerrando esta deuda de prueba.
- **Comprobación ejecutable:**
  ```
  uv run pytest -q tests/test_projects.py
  uv run pytest -q
  uv run ruff check .
  ```
  Los dos casos de `DELETE` que sí se pueden probar (`204` sin tareas,
  `404` inexistente) pasan; la suite completa y el linter siguen en verde.
  Esta comprobación **no** cubre la rama `409` — ver limitación arriba.

### Incremento 5 — Orden estable y esquema exacto en `GET /projects`

- Test primero: crear varios proyectos, pedir `GET /projects` dos veces
  seguidas y comparar que ambas respuestas son idénticas y están en orden de
  `id` ascendente; comparar que cada elemento tiene exactamente los campos
  `id`, `name`, `description` (ni más ni menos), con `description` nulo
  serializado como `null` cuando no se envió.
- Este incremento no debería requerir cambios de implementación si los
  incrementos 1–2 ya construyeron la consulta con `ORDER BY id` y el
  esquema de salida estricto; existe como incremento separado porque la
  matriz mínima de tests del contrato lo pide como caso explícito
  ("Orden estable" y "Esquema de respuesta exacto") y merece su propio
  commit de test si no quedó cubierto antes. Si al revisar el Incremento 2
  ya quedó cubierto con los mismos tests, este incremento se fusiona con el
  2 y no se ejecuta por separado.
- **Comprobación ejecutable:**
  ```
  uv run pytest -q tests/test_projects.py
  uv run pytest -q
  uv run ruff check .
  ```
  Los casos de orden estable y esquema exacto pasan; la suite completa y el
  linter siguen en verde.
