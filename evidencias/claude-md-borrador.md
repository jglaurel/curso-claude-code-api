# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

TaskFlow API, a FastAPI service built incrementally as part of a course. The current entry
(`app/main.py`) only exposes `GET /health`; projects, tasks, states, and due-date filtering are
specified in the contract but not yet implemented.

## Commands

```bash
uv sync --locked              # install exact dependencies from the lockfile
uv run pytest -q              # run tests
uv run pytest -q tests/test_health.py::test_health_returns_200_and_ok_body  # single test
uv run ruff check .           # lint
docker compose up -d          # start PostgreSQL
docker compose down           # stop it
uv run uvicorn app.main:app --reload   # run the API locally
```

There is no build step; `uv run` executes directly against the venv defined by `pyproject.toml`/`uv.lock`.

## Sources of truth (read before changing behavior)

- **`docs/contrato-api.md`** fixes all observable API behavior — status codes, response schemas,
  ordering, error shapes. It is what the tests assert and what later course sessions compare
  against. Only change it when a ticket explicitly says the contract changes, and if so, update
  the contract in a commit separate from the code/test change.
- **`docs/decisiones-ingenieria.md`** records team engineering decisions that aren't derivable from
  the code. Key ones:
  - Persistence tests run against **PostgreSQL only** — SQLite is explicitly rejected because it
    doesn't reproduce the same constraints, types, or migrations.
  - Schema changes go through **Alembic migrations** with both `upgrade` and `downgrade`
    implemented and tested in both directions; nothing is created as a side effect of importing a
    module.
  - The `states` catalog (`PENDIENTE`, `EN_CURSO`, `BLOQUEADA`, `HECHA`) is seeded via migration
    (not a Docker init script), so it reaches every environment on every `upgrade`, and the seed
    must be idempotent.
  - TDD discipline: a new capability starts with a failing test. Never weaken or delete an existing
    test to turn it green — if the agreed behavior changed, the contract changes first, then the
    test, in a separate commit.
- **`README.md`** contains the canonical setup/run commands for this repo.

## Contract details worth remembering

- Errors are `{"detail": "<message>"}`; `404` for missing resource, `409` for conflict, `422` for
  invalid input. A reference to a nonexistent project/state is never created implicitly.
- `title` normalization: trim, then reject with `422` if no visible character remains. `strip()`
  alone is not enough — invisible Unicode (e.g. `U+200B`) must be caught by rejecting categories
  `Cc`, `Cf`, `Zl`, `Zp`, `Zs`.
- Collection endpoints return a stable order across identical calls: `GET /states` by catalog
  order then `id`; `GET /projects` and `GET /tasks` by `id` ascending (filters don't change this).
- Response schemas are exact — an optional field absent is serialized as `null`, never omitted; no
  extra fields.
- `due_at` (task v2) is optional, must include a timezone on input (naive datetime → `422`), and is
  always serialized in UTC with a trailing `Z`, no offset, no microseconds.
- `GET` collections return a bare JSON array, never an object wrapper.
- Deleting a project with tasks returns `409`, not cascading delete.

## Local data / secrets

- `.env` may contain secrets — do not open, display, edit, or commit it. `.env.example` is the
  only source to consult for variable names; real values are configured outside the conversation.
