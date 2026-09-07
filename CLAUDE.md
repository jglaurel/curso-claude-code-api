# CLAUDE.md

Guía para Claude Code en el repositorio TaskFlow API.

## Fuentes de verdad

- `docs/contrato-api.md` fija el comportamiento observable de la API. Solo se
  modifica cuando un ticket lo pide explícitamente, y en un commit separado
  del código o los tests.
- `docs/decisiones-ingenieria.md` registra las decisiones de ingeniería del
  equipo que no se deducen del código.
- `README.md` tiene los comandos canónicos de instalación y puesta en marcha.

## Comandos esenciales

- Instalar dependencias: `uv sync --locked`
- Tests: `uv run pytest -q`
- Lint: `uv run ruff check .`

Puesta en marcha completa (Docker, servidor, variables de entorno) en
`README.md`.

## Persistencia

Las pruebas que ejercitan persistencia corren solo contra PostgreSQL. SQLite
no se usa en ningún test: no reproduce las mismas restricciones, tipos ni
migraciones. Detalle en `docs/decisiones-ingenieria.md`.

## Datos locales

`.env` no se abre, no se muestra, no se edita ni se confirma. Para nombres de
variables, consultar `.env.example`.

## Disciplina de tests

Un test existente no se debilita ni se elimina para conseguir verde. Si el
comportamiento acordado cambió, se actualiza primero `docs/contrato-api.md` y
después el test, en commits separados.
