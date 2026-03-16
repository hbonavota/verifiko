# Verifiko Backend

Verifiko is a signal-based verification engine backend focused on explainable risk assessment for suspicious digital content.

The current codebase includes a usable domain scoring flow, application use cases, and a minimal FastAPI layer backed by an in-memory repository. PostgreSQL and SQLAlchemy scaffolding are present, but persistent storage is not wired yet.

## Tech Stack

- Python 3.11+
- FastAPI
- SQLAlchemy
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

2. Install dependencies:

```bash
pip install -e .
```

3. Start the API:

```bash
uvicorn app.entrypoints.api.main:app --reload --host 0.0.0.0 --port 8000
```

4. Health check:

```bash
curl http://localhost:8000/health
```

5. Create a verification:

```bash
curl -X POST http://localhost:8000/api/verifications \
  -H "Content-Type: application/json" \
  -d '{
    "url": "verifiko.es/login",
    "signals": [
      {
        "signal_type": "BRAND_IMPERSONATION",
        "category": "CONTENT_BEHAVIOR",
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

API URL: `http://localhost:8000`

## Current API Surface

- `GET /health`
- `POST /api/verifications`
- `GET /api/verifications`
- `GET /api/verifications/{verification_id}`

## Known Gaps

- SQLAlchemy models and repository persistence are still pending.
- External analyzer clients are reserved for later integration work.
