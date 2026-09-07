# TaskFlow API

API de TaskFlow construida con FastAPI. El comportamiento observable está
fijado en [`docs/contrato-api.md`](docs/contrato-api.md). Esta primera
entrega solo expone `GET /health`.

## Requisitos

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Docker y Docker Compose

## Puesta en marcha

```bash
# 1. Variables de entorno locales (opcional para esta entrega; compose.yaml
#    ya trae valores por defecto seguros si no existe .env)
cp .env.example .env

# 2. Instalar dependencias exactas del lockfile
uv sync --locked

# 3. Ejecutar la suite de tests
uv run pytest -q

# 4. Analizar el código con Ruff
uv run ruff check .

# 5. Levantar PostgreSQL
docker compose up -d

# 6. Arrancar la API (queda expuesta como app.main:app)
uv run uvicorn app.main:app --reload

# 7. Verificar la salud del servicio
curl http://localhost:8000/health

# 8. Al terminar, apagar los servicios de Docker
docker compose down
```
