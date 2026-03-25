# Verifiko API

Verifiko is a signal-based verification API focused on explainable risk assessment for suspicious digital content.

The current codebase includes a usable domain scoring flow, application use cases, and a FastAPI layer backed by a SQLAlchemy repository. Verifications now persist to the configured PostgreSQL database.

## Tech Stack

- Python 3.11+
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Docker / Docker Compose

## Project Structure

```text
app/
  domain/
  application/
  infrastructure/
  entrypoints/

tests/
  unit/
  integration/
```

## Local Run

1. Create environment file:

```bash
cp .env.example .env
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -e ".[dev]"
```

4. Start PostgreSQL locally:

Using Docker Compose for PostgreSQL:

```bash
docker compose up -d db
```

5. Run database migrations:

```bash
alembic upgrade head
```

6. Start the API:

```bash
uvicorn app.entrypoints.api.main:app --reload --host 0.0.0.0 --port 8000
```

7. Health check:

```bash
curl http://localhost:8000/health
```

8. Run tests:

```bash
python -m pytest
```

9. Create a verification:

```bash
curl -X POST http://localhost:8000/api/verifications \
  -H "Content-Type: application/json" \
  -d '{
    "url": "verifiko.es/login",
    "signals": [
      {
        "signal_type": "brand_impersonation",
        "category": "content_behavior",
        "severity": "HIGH",
        "confidence": 92,
        "title": "Brand impersonation",
        "description": "Brand styling copied from the legitimate destination.",
        "source": "content-analyzer"
      }
    ]
  }'
```

## Docker Run

1. Create environment file:

```bash
cp .env.example .env
```

2. Start services:

```bash
docker compose up --build
```

3. Run migrations:

```bash
alembic upgrade head
```

API URL: `http://localhost:8000`

## Vercel Deployment

This API is intended to be deployed as its own Vercel project with Root Directory `api/`.

Runtime expectations:

- Vercel discovers the FastAPI application from `index.py`.
- The application does not run database migrations at startup.
- A real `DATABASE_URL` must be provided through Vercel environment variables.

Required environment variables:

- `DATABASE_URL`
- `CORS_ALLOWED_ORIGINS` for the deployed frontend origin
- `APP_DEBUG=false`

Optional environment variables:

- `CORS_ALLOWED_ORIGIN_REGEX` for controlled preview-origin access

Deploy checklist:

1. Provision the production database.
2. Run the migration command against that database outside the Vercel request runtime:

```bash
source .venv/bin/activate
DATABASE_URL='YOUR_PRODUCTION_DATABASE_URL' python -m alembic upgrade head
```

3. Deploy the `api` Vercel project.
4. Verify `GET /health`.
5. Verify `POST /api/verifications`.

Notes:

- The verification request path performs synchronous outbound checks for RDAP, HTML fetching, and TLS validation. Those calls are bounded and degrade gracefully, but they can increase response time.
- The current implementation is suitable for a first deployment, not for claiming full production hardening.
- For custom-domain cutover, update `CORS_ALLOWED_ORIGINS` from the temporary frontend Vercel URL to `https://verifiko.es` after the `web` project is attached to the final domain.

## Current API Surface

- `GET /health`
- `POST /api/verifications`
- `GET /api/verifications`
- `GET /api/verifications/{verification_id}`

## Known Gaps

- The API no longer bootstraps schema automatically; migrations must be applied explicitly before startup.
- Some analyzers perform request-time outbound lookups and degrade gracefully when those checks fail.
