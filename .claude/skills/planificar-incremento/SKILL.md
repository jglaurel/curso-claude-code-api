---
name: planificar-incremento
description: Planifica un incremento de trabajo contra el contrato y las decisiones de ingeniería de TaskFlow, en incrementos numerados con comprobación ejecutable, sin implementar código.
---

# Planificar incremento

Uso: `/planificar-incremento <descripción del incremento o ticket>`

Esta skill produce un plan en `docs/`. No escribe ni modifica código de la
aplicación, no instala dependencias, no toca la base de datos ni ejecuta
migraciones. Si algún punto del incremento requiere comprobar algo
ejecutando código, eso se declara como el criterio de comprobación de ese
incremento — no se ejecuta aquí.

## 1. Leer las fuentes antes de planificar

Antes de proponer nada, leer en este orden:

- `docs/contrato-api.md` — fija el comportamiento observable que el
  incremento debe alcanzar o respetar.
- `docs/decisiones-ingenieria.md` — decisiones del equipo no derivables del
  código (persistencia, migraciones, disciplina de tests).
- `README.md` — comandos canónicos de instalación, tests y arranque.
- `CLAUDE.md` — guía operativa vigente para trabajar en este repo.
- El estado real del repositorio: `git status`, `git log --oneline -15` y
  los archivos relevantes al incremento (rutas, modelos, tests
  existentes). No se asume el estado: se comprueba.

Si ya existe un `docs/plan-*.md` sobre el mismo tema, se lee también: un
plan nuevo no repite ni contradice uno vigente sin decirlo explícitamente.

## 2. Escribir el plan en docs/

- Archivo nuevo en `docs/`, nombrado `plan-<tema>.md`, donde `<tema>`
  identifica de qué es el plan (p. ej. `docs/plan-proyectos.md`) — no un
  nombre genérico como `plan.md` o `plan-nuevo.md`.
- El documento abre indicando qué cubre, contra qué fuentes se planificó
  (citando los documentos del paso 1) y el estado del repositorio al
  planificar (qué ya existe, qué falta).

## 3. Incrementos numerados con comprobación ejecutable

- El trabajo se divide en incrementos numerados (`Incremento 1`,
  `Incremento 2`, ...), cada uno con alcance propio, pensado como un
  commit que se confirma antes de seguir con el siguiente.
- Cada incremento declara su propia **comprobación ejecutable**: un
  comando o test concreto que se puede correr para verificar que quedó
  bien hecho (p. ej. `uv run pytest -q tests/test_projects.py`, o una
  secuencia de `alembic upgrade`/`downgrade` a comprobar). No basta con
  describir en prosa el resultado esperado.

## 4. Ninguna decisión aplazada

- Si un punto del incremento no se puede decidir con lo que hay en el
  contrato, las decisiones de ingeniería o el estado del repositorio,
  **no se propone en condicional** ("se podría", "probablemente",
  "quizás convenga"). El plan se detiene en ese punto y se pregunta
  directamente, nombrando qué falta decidir y por qué el repositorio no lo
  resuelve por sí solo.
- Un plan con huecos sin decidir no se entrega como si estuviera completo.

## 5. Fuera de alcance

- El plan incluye una sección explícita de qué queda fuera de alcance de
  este incremento (funcionalidad relacionada que no se toca, decisiones
  que pertenecen a otro ticket, etc.), igual que hace
  `docs/plan-persistencia.md`.

## Límites de esta skill

- Planifica, no implementa: no crea ni edita archivos de código de la
  aplicación, no corre `uv sync`, no instala ni actualiza dependencias, y
  no ejecuta migraciones ni toca la base de datos, ni siquiera para
  explorar el esquema.
- La única escritura que hace esta skill es el archivo de plan en
  `docs/`.
