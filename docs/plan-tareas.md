# Plan: recurso Tareas (v1 y v2 completas)

Cubre las secciones **Tareas v1** y **Tareas v2: Fechas Límite** de
`docs/contrato-api.md` completas: CRUD de `/tasks`, filtros de
`GET /tasks` (`project_id`, `state_id`, combinados), y en v2 el campo
`due_at` con normalización a UTC y el filtro `overdue=true`.

Cada incremento es un commit que se confirma solo; al terminar uno se para
y se espera aprobación antes del siguiente.

## Fuentes consultadas

- `docs/contrato-api.md` — secciones Tareas v1 y Tareas v2 (campos, rutas,
  códigos de estado, normalización de texto de `title`, orden de listas,
  esquema de respuesta exacto, matriz mínima de tests), y las convenciones
  generales (`404`/`409`/`422`, forma de error `{"detail": ...}`, "una
  referencia a proyecto o estado inexistente no se crea implícitamente").
- `docs/decisiones-ingenieria.md` — persistencia solo contra PostgreSQL,
  migraciones de Alembic escritas a mano con `upgrade`/`downgrade` probados
  en ambos sentidos, disciplina de tests (capacidad nueva empieza con un
  caso que falla; no se debilita un test existente).
- `README.md` — comandos canónicos (`uv sync --locked`, `uv run pytest -q`,
  `uv run ruff check .`, `docker compose up -d`, `alembic upgrade head` /
  `downgrade -1` / `downgrade base`).
- `CLAUDE.md` — guía operativa vigente.
- `docs/plan-persistencia.md` y `docs/plan-proyectos.md` — planes previos
  del mismo repositorio: fijan el patrón de incrementos ya ejecutado para
  Salud, Estados y Proyectos. Este plan no repite esos recursos; los da por
  hechos y sigue el mismo patrón para Tareas. En particular,
  `docs/plan-proyectos.md` (Incremento 4) dejó declarada una deuda de
  prueba explícita: la rama `409` de `DELETE /projects/{id}` con tareas
  asociadas quedó implementada pero sin test por ejecución, a la espera de
  que existiera la tabla `tasks`. Este plan la cierra (ver Incremento 3).
- Estado real del repositorio (`git status`, `git log --oneline -15`, y
  lectura directa de `app/main.py`, `app/db.py`, `app/config.py`,
  `tests/`, `alembic/versions/`, `pyproject.toml`, `compose.yaml`).

## Estado del repositorio al planificar

- Rama actual: `feature/tasks`, creada desde `main` (limpio, sincronizado
  con `origin/main`). Migraciones existentes ya aplicadas contra
  PostgreSQL levantado con `docker compose up -d` (`alembic current` →
  `ba948a7595c2 (head)`).
- `app/main.py` implementa `GET /health`, `GET /states`, y CRUD completo
  de `/projects` (`POST`, `GET` lista, `GET` por id, `PATCH`, `DELETE`)
  con SQLAlchemy Core (`sa.table`, sin ORM) vía `get_engine()`
  (`app/db.py`). **Ya declara** `_tasks_table = sa.table("tasks",
  sa.column("id", sa.Integer), sa.column("project_id", sa.Integer))` y una
  función `_project_has_tasks(connection, project_id)` usada por `DELETE
  /projects/{id}` para decidir el `409`. Esa función hoy captura
  `sa.exc.ProgrammingError` (la tabla `tasks` no existe todavía) y hace
  `rollback()` + devuelve `False` — es la "deuda técnica temporal"
  documentada en su propio docstring, a resolver cuando exista la
  migración real de `tasks`. Este plan la elimina en el Incremento 1 (una
  vez existe la tabla, ya no hay excepción que capturar) y la reemplaza
  por la comprobación real, sin el `try/except`.
- `_tasks_table` declarada en `app/main.py` solo tiene `id` y
  `project_id`: no alcanza para implementar Tareas como recurso; este plan
  la reemplaza por una declaración completa con todas las columnas del
  contrato (`title`, `description`, `state_id`, y en v2 `due_at`).
- No existe ninguna tabla `tasks` en el esquema real, ninguna migración
  para ella, ningún endpoint de `/tasks`, y ningún `tests/test_tasks.py`.
  Se parte de cero para las rutas y la persistencia de Tareas, pero no de
  cero para la comprobación de tareas asociadas a un proyecto: esa lógica
  ya existe y se ajusta, no se crea.
- `app/config.py`: `Settings` como `dataclass` congelada desde variables
  `POSTGRES_*`; no expone nada específico de tareas ni fechas.
- `alembic/env.py`: `target_metadata = None`, sin autogenerate; las
  migraciones se escriben a mano. Dos migraciones existentes:
  `501de659f4ac_create_states_catalog.py` (base, con seed idempotente vía
  `ON CONFLICT DO NOTHING`) y `ba948a7595c2_create_projects_table.py`
  (`down_revision` apunta a la primera). La nueva migración de `tasks`
  encadena con `down_revision = 'ba948a7595c2'`.
- `tests/conftest.py`: fixtures `db_engine` (sesión, PostgreSQL real) y
  `db_connection` (transacción por test con rollback) — reutilizables tal
  cual. `tests/test_projects.py` fija el patrón de estrategia de datos:
  crear vía `POST` a través de `TestClient` (la misma conexión que usa la
  app), nunca insertar directo con `db_connection` para datos que la app
  debe ver, porque esa conexión abre su propia transacción con rollback y
  nunca hace commit. Se sigue el mismo patrón para `tasks`.
- `pyproject.toml`: dependencias ya declaradas — `fastapi`, `sqlalchemy`,
  `psycopg[binary]`, `alembic`, y de desarrollo `httpx`, `pytest`, `ruff`.
  Python `>=3.12,<3.13`. **No hace falta añadir ninguna dependencia
  nueva**: la normalización Unicode de `title` se resuelve con el módulo
  estándar `unicodedata` (categorías `Cc`, `Cf`, `Zl`, `Zp`, `Zs`, tal como
  las nombra el contrato) y el manejo de fechas con zona horaria se
  resuelve con `datetime` de la librería estándar más el tipo `DateTime(timezone=True)`
  de SQLAlchemy sobre PostgreSQL (`TIMESTAMPTZ`), sin librerías externas.
- No hay ningún `docs/plan-tareas.md` previo con el que este documento
  pudiera entrar en conflicto.

## Decisiones que sí resuelve el contrato (no se preguntan)

- **Algoritmo de normalización de `title`:** el contrato ya lo fija
  completo en la sección "Normalización de texto": recortar espacio de los
  extremos: y luego rechazar con `422` si no queda ningún carácter cuya
  categoría Unicode sea distinta de `Cc`, `Cf`, `Zl`, `Zp`, `Zs`. No es una
  decisión abierta: es una implementación directa de `unicodedata.category()`
  carácter por carácter sobre el string ya recortado.
- **Instante de evaluación de `overdue`:** el contrato dice "anterior al
  instante de evaluación", que es el momento en que se procesa la petición
  `GET /tasks?overdue=true` — no un parámetro de entrada ni una fecha
  fija. Se resuelve comparando `due_at < now()` en la propia consulta
  (`sa.func.now()` del lado de PostgreSQL, para no depender de relojes
  distintos entre la app y la base), combinado con `state_id` distinto del
  id correspondiente a `HECHA`. Una tarea con `due_at is null` nunca
  cumple `due_at < now()`, así que queda excluida sin lógica adicional.
- **Serialización de `due_at`:** el contrato fija el formato exacto
  (`2026-03-01T09:00:00Z`, UTC, con `Z`, sin microsegundos, sin
  desplazamiento `+00:00`). Se resuelve normalizando a UTC al guardar
  (columna `TIMESTAMPTZ`, valor convertido a UTC antes del `INSERT`/`UPDATE`)
  y formateando a mano en la serialización de salida en vez de confiar en
  el `isoformat()` por defecto de Python, que produce `+00:00` en vez de
  `Z` y conserva microsegundos si los hay.
- **Rechazo de fecha sin zona:** el contrato es explícito — "no supone
  ninguna por su cuenta". Un `due_at` de entrada sin información de zona
  horaria (`datetime.tzinfo is None` tras el parseo) se rechaza con `422`,
  sin asumir UTC ni la zona del servidor.

## Fuera de alcance

- Recordatorios, scheduler, zona horaria preferida del usuario y cambio
  automático de estado al vencer: excluidos explícitamente por el
  contrato en la sección Tareas v2.
- Autenticación, autorización o cualquier control de acceso a `/tasks`.
- Paginación de `GET /tasks`: el contrato solo exige orden determinista
  por `id` ascendente, también con filtros aplicados; no pide paginar.
- Cualquier campo de tarea más allá de `id`, `title`, `description`,
  `project_id`, `state_id`, `due_at`: el contrato fija esos como "ni más
  ni menos".
- Cambios al contrato: si aparece una ambigüedad nueva no cubierta por
  este plan durante la implementación, se resuelve actualizando primero
  `docs/contrato-api.md` en un commit separado, según exige `CLAUDE.md`.
- Documentación de arranque/migraciones en `README.md`: ya cubre el flujo
  de Alembic genérico; no hace falta un comando nuevo específico para
  tareas.
- Modificar `docs/plan-proyectos.md`: la deuda de prueba que ese plan dejó
  declarada se cierra con un test nuevo en `tests/test_projects.py` (ver
  Incremento 3), pero el documento del plan de Proyectos no se edita —
  quedó como registro histórico de lo que se decidió en su momento.

## Incrementos

### Incremento 1 — Migración: tabla `tasks` (v1, sin `due_at`)

- Nueva migración de Alembic (`down_revision = 'ba948a7595c2'`) que crea
  la tabla `tasks` con:
  - `id`: entero, clave primaria autogenerada.
  - `title`: string, `nullable=False`.
  - `description`: string, `nullable=True`.
  - `project_id`: entero, `nullable=False`, clave foránea a `projects.id`.
  - `state_id`: entero, `nullable=False`, clave foránea a `states.id`.
  - Sin `ON DELETE CASCADE` en ninguna de las dos claves foráneas: el
    contrato exige `409` al borrar un proyecto con tareas en vez de
    borrado en cascada implícito, así que la base tampoco debe permitirlo
    por su cuenta.
  - Sin seed: las filas las crea la API, igual que `projects`.
- `downgrade()` elimina la tabla.
- Ajuste en `app/main.py`: se reemplaza la declaración parcial de
  `_tasks_table` (solo `id`, `project_id`) por una completa con todas las
  columnas de v1, y se simplifica `_project_has_tasks` quitando el
  `try/except sa.exc.ProgrammingError` — ya no hace falta, la tabla existe
  siempre que la migración esté aplicada.
- **Comprobación ejecutable:**
  ```
  docker compose up -d
  uv run alembic upgrade head
  uv run alembic downgrade -1
  uv run alembic upgrade head
  ```
  Sube sin error, baja sin error (la tabla `tasks` desaparece), y volver a
  subir la recrea limpia.

### Incremento 2 — `POST /tasks` y `GET /tasks/{id}`

- Test primero (falla por ausencia de la capacidad): `POST /tasks` con
  `title`, `project_id` y `state_id` válidos responde `201` con el
  recurso creado y esquema exacto v1 (`id`, `title`, `description`,
  `project_id`, `state_id` — sin `due_at`, que es de v2); `POST` con
  `project_id` inexistente responde `422` y no crea la tarea; `POST` con
  `state_id` inexistente responde `422` y no crea la tarea; `POST` con
  `title` vacío o solo espacios ASCII responde `422`; `GET /tasks/{id}`
  responde `200` para una tarea existente y `404` para una inexistente.
- Implementación: rutas en `app/main.py` siguiendo el patrón de
  `/projects` (SQLAlchemy Core vía `get_engine()`, sin ORM). Antes de
  insertar, `POST /tasks` comprueba que `project_id` y `state_id`
  referencian filas existentes (`SELECT EXISTS`) y responde `422` sin
  crear nada si alguno falta — el contrato dice "una referencia a
  proyecto o estado inexistente no se crea implícitamente", y agrupa esto
  bajo "valida proyecto, estado y título" en la misma familia de error
  `422` que el título inválido. Normalización de `title`: función
  dedicada (recorte + comprobación de categoría Unicode por carácter
  sobre `Cc`, `Cf`, `Zl`, `Zp`, `Zs`) reutilizada también por `PATCH`
  (Incremento 4).
- **Comprobación ejecutable:**
  ```
  uv run pytest -q tests/test_tasks.py
  uv run pytest -q
  uv run ruff check .
  ```
  Los tests nuevos pasan, la suite completa sigue en verde, el linter no
  reporta hallazgos.

### Incremento 3 — `DELETE /tasks/{id}` y cierre de la deuda de `DELETE /projects/{id}` → `409`

- Test primero: `DELETE /tasks/{id}` sobre una tarea existente responde
  `204` sin cuerpo y la tarea deja de existir (`GET` posterior da `404`);
  sobre un `id` inexistente responde `404`.
- Implementación: ruta de borrado directa, mismo patrón que `DELETE
  /projects/{id}` sin la comprobación de dependientes (nada en el
  contrato referencia `tasks` como padre de otro recurso).
- Cierra la deuda de prueba declarada en `docs/plan-proyectos.md`
  (Incremento 4): con la tabla `tasks` ya existente desde el Incremento 1
  de este plan, se añade a `tests/test_projects.py` el test que faltaba —
  crear un proyecto, crear una tarea asociada vía `POST /tasks`, y
  comprobar que `DELETE /projects/{id}` sobre ese proyecto responde `409`
  sin borrarlo (`GET /projects/{id}` posterior sigue en `200`). Este test
  vive en `test_projects.py`, no en `test_tasks.py`, porque ejercita el
  contrato de Proyectos, aunque dependa de la tabla de Tareas para
  construir el escenario.
- **Comprobación ejecutable:**
  ```
  uv run pytest -q tests/test_tasks.py tests/test_projects.py
  uv run pytest -q
  uv run ruff check .
  ```
  Los casos de `DELETE /tasks/{id}` pasan; el test de `409` en
  `test_projects.py` pasa (cierra la deuda declarada); la suite completa y
  el linter siguen en verde.

### Incremento 4 — `PATCH /tasks/{id}` y actualización parcial consistente

- Test primero: `PATCH` con solo `description` deja el resto intacto;
  `PATCH` con `project_id` hacia un proyecto inexistente responde `422` y
  no modifica la tarea; `PATCH` con `state_id` hacia un estado inexistente
  responde `422` y no modifica la tarea; `PATCH` con `title` vacío o solo
  espacios responde `422` y no modifica la tarea; `PATCH` sobre un `id`
  inexistente responde `404`; la respuesta tiene el esquema exacto v1.
  "Actualización parcial consistente" (texto del contrato) se interpreta
  como: cada campo presente en el cuerpo se valida con las mismas reglas
  que en `POST` antes de aplicar ningún cambio — no se permite dejar la
  fila en un estado que `POST` habría rechazado.
- Implementación: reutiliza la función de normalización de `title` y las
  comprobaciones de existencia de `project_id`/`state_id` del
  Incremento 2, aplicadas solo a los campos presentes en
  `payload.model_dump(exclude_unset=True)`.
- **Comprobación ejecutable:**
  ```
  uv run pytest -q tests/test_tasks.py
  uv run pytest -q
  uv run ruff check .
  ```
  Los casos de `PATCH` pasan; el resto de `test_tasks.py` y la suite
  completa siguen en verde.

### Incremento 5 — `GET /tasks` con filtros (`project_id`, `state_id`, combinados) y orden estable

- Test primero: `GET /tasks` sin filtros responde `200` con lista JSON en
  la raíz, orden `id` ascendente, estable entre dos llamadas idénticas;
  `GET /tasks?project_id=X` devuelve solo tareas de ese proyecto;
  `GET /tasks?state_id=Y` devuelve solo tareas de ese estado;
  `GET /tasks?project_id=X&state_id=Y` combina ambos filtros (intersección,
  no unión); cada elemento tiene el esquema exacto v1.
- Implementación: query con `WHERE` condicional según los parámetros
  presentes, `ORDER BY id` siempre aplicado (el contrato dice
  explícitamente "también con filtros aplicados").
- **Comprobación ejecutable:**
  ```
  uv run pytest -q tests/test_tasks.py
  uv run pytest -q
  uv run ruff check .
  ```
  Los casos de filtros solos, combinados y orden estable pasan; la suite
  completa y el linter siguen en verde.

### Incremento 6 — Migración v2: columna `due_at`

- Nueva migración de Alembic (`down_revision` apuntando a la migración del
  Incremento 1) que añade a `tasks` la columna `due_at`:
  `sa.Column("due_at", sa.DateTime(timezone=True), nullable=True)` — usa
  `TIMESTAMPTZ` en PostgreSQL, `nullable=True` porque el contrato dice que
  omitirlo conserva compatibilidad v1.
- `downgrade()` elimina la columna (`op.drop_column`), dejando el esquema
  exactamente como al final del Incremento 1.
- **Comprobación ejecutable:**
  ```
  docker compose up -d
  uv run alembic upgrade head
  uv run alembic downgrade -1
  uv run alembic upgrade head
  ```
  Sube sin error (columna `due_at` aparece), baja sin error (columna
  desaparece, resto de `tasks` intacto), y volver a subir la recrea.
  Cubre explícitamente el caso de la matriz mínima "migración desde base
  vacía y rollback de v2": se comprueba además subiendo desde cero
  (`downgrade base` → `upgrade head`) en la misma sesión de verificación
  manual, no solo el paso a paso de una revisión.

### Incremento 7 — `due_at` en `POST` y `PATCH /tasks`: validación, normalización a UTC y serialización

- Test primero: `POST /tasks` sin `due_at` sigue respondiendo `201` con
  `due_at: null` (compatibilidad v1); `POST` con `due_at` en una zona
  distinta de UTC (p. ej. `-03:00`) responde `201` con `due_at` serializado
  en UTC con sufijo `Z` y sin microsegundos; `POST` con `due_at` sin
  información de zona responde `422`; `PATCH` con `due_at` válido lo
  actualiza; `PATCH` con `due_at: null` explícito lo limpia; `PATCH` con
  `due_at` sin zona responde `422` y no modifica la tarea.
- Implementación: `due_at` se añade a los modelos `TaskCreate`/`TaskUpdate`
  como `datetime | None`; Pydantic ya rechaza con `422` un string que no
  parsea a fecha, pero **no** distingue por sí solo "sin zona" de "con
  zona" de forma que cumpla el contrato — se añade un validador explícito
  que comprueba `value.tzinfo is not None` (y `utcoffset()` no nulo) y
  levanta el `422` si falta. Al guardar, se convierte a UTC
  (`value.astimezone(UTC)`) antes del `INSERT`/`UPDATE`. Al serializar la
  salida, se formatea a mano
  (`value.strftime("%Y-%m-%dT%H:%M:%S") + "Z"` sobre el valor ya en UTC y
  sin microsegundos) en vez de usar `isoformat()`, para cumplir el formato
  exacto del contrato.
- Ajuste de esquema de salida: `_task_to_dict` (o equivalente) pasa a
  incluir `due_at` siempre, como `null` si no tiene valor — el contrato
  fija que un campo opcional ausente se devuelve como `null`, no se omite.
- **Comprobación ejecutable:**
  ```
  uv run pytest -q tests/test_tasks.py
  uv run pytest -q
  uv run ruff check .
  ```
  Los casos de `due_at` omitido, con zona, sin zona, y `PATCH` a `null`
  pasan; la suite completa y el linter siguen en verde.

### Incremento 8 — `GET /tasks?overdue=true`

- Test primero: una tarea con `due_at` en el pasado y estado distinto de
  `HECHA` aparece en `GET /tasks?overdue=true`; una tarea con `due_at` en
  el pasado pero estado `HECHA` no aparece; una tarea con `due_at` en el
  futuro no aparece; una tarea sin `due_at` no aparece; `overdue=true`
  combinado con `project_id` y/o `state_id` sigue siendo intersección de
  todos los filtros presentes; sin el parámetro `overdue` (u
  `overdue=false`), el comportamiento de `GET /tasks` no cambia respecto
  al Incremento 5.
- Implementación: condición adicional en el `WHERE` de `GET /tasks`,
  activa solo cuando `overdue=true` está presente:
  `due_at < sa.func.now()` (evaluado del lado de PostgreSQL, no con
  `datetime.now()` de Python, para no depender del reloj del proceso de
  la app) `AND state_id != <id de HECHA>`. El id de `HECHA` se resuelve
  con una subconsulta contra `states` por `code`, no hardcodeado como
  entero, porque nada en el contrato garantiza que `HECHA` tenga un `id`
  fijo entre entornos (el seed usa `ON CONFLICT DO NOTHING`, no reinserta
  con id explícito).
- **Comprobación ejecutable:**
  ```
  uv run pytest -q tests/test_tasks.py
  uv run pytest -q
  uv run ruff check .
  ```
  Los seis casos de `overdue` (vencida no-HECHA, vencida-HECHA, futura,
  sin fecha, combinado con otros filtros, ausente) pasan; la suite
  completa y el linter siguen en verde.

### Incremento 9 — Regresión Unicode de `title` (sesión 7) y matriz mínima final

- Test primero, específicamente sobre la normalización de `title` con
  invisibles Unicode que `strip()` no atraviesa: un `title` compuesto
  solo por `U+200B` (zero-width space, categoría `Cf`) responde `422`;
  un `title` con espacio ASCII normal más `U+200B` en los extremos y
  contenido visible en el medio se acepta y persiste ya recortado; un
  `title` compuesto solo por combinaciones de categorías `Cc`, `Cf`,
  `Zl`, `Zp`, `Zs` (sin usar necesariamente el mismo carácter que el
  primer caso) responde `422`. Estos casos existen ya sea que el
  Incremento 2 los haya cubierto de forma incompleta o no: si la función
  de normalización se implementó correctamente por categoría desde el
  Incremento 2, este incremento no cambia código de `app/`, solo añade
  los tests que faltan como regresión explícita.
- Revisión de cierre contra la Matriz Mínima de Tests del contrato
  completa (no solo la parte de `title`): confirma con una pasada de
  `test_tasks.py` que están cubiertos todos los puntos que tocan Tareas —
  CRUD feliz, IDs inexistentes, proyecto/estado inexistente al crear,
  filtros solos y combinados, orden estable, esquema exacto,
  `due_at` en sus seis variantes. No añade tests nuevos más allá de los
  Unicode si todo lo demás ya quedó cubierto en los incrementos previos;
  si al revisar aparece un hueco no cubierto, este incremento lo cierra.
- **Comprobación ejecutable:**
  ```
  uv run pytest -q tests/test_tasks.py
  uv run pytest -q
  uv run ruff check .
  ```
  Los tres casos Unicode pasan; la suite completa y el linter siguen en
  verde. Con esto, Tareas v1 y v2 quedan completas contra el contrato.
