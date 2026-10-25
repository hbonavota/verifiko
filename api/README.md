# Verifiko API

The FastAPI service behind [Verifiko](../README.md). The root README covers the product overview,
architecture, detection engine and security model. The full endpoint contract, with auth, scans,
webhooks, quotas and errors, is in [`docs/API.md`](../docs/API.md).

## Layout

```text
app/
  domain/          entities, value objects, enums, scoring policy, compound rules (no I/O)
  application/     use cases, DTOs, signal analyzers, ports
  infrastructure/  adapters: persistence, security, reputation, fetchers, detonation, storage, email
  entrypoints/api/ FastAPI routes, schemas, DI container (dependencies/container.py)
alembic/           schema migrations
evaluation/        offline detection-quality harness and labeled corpus
tests/             unit/ and integration/
index.py           Vercel entrypoint
```

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # every setting is documented inline
docker compose up -d db
alembic upgrade head
uvicorn app.entrypoints.api.main:app --reload --port 8000
```

Or run the API and Postgres together with `docker compose up --build`, then
`alembic upgrade head`.

Smoke test:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/verifications \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

The versioned `/api/v1` routes are the documented contract. The same routes are also mounted
under `/api` for the existing web client, hidden from the OpenAPI schema.

## Tests and detection quality

```bash
python -m pytest -q
python -m evaluation.run_evaluation
ruff check . && black --check .
```

All must stay green before a change is merged, and the evaluation must not regress precision.
Lint and format config live in `pyproject.toml`; `black .` and `ruff check --fix .` apply fixes.

## Deploy

The service deploys as its own Vercel project with Root Directory `api/`. Migrations are applied
before the code that needs them, never at app startup. See [`DEPLOY.md`](DEPLOY.md).
