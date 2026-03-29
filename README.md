# Verifiko

Verifiko is a portfolio-grade verification workspace for suspicious digital content, built to demonstrate explainable scoring, evidence traceability, and operational review workflows.

## System Status

- The backend verification pipeline is real and exposed through FastAPI routes.
- The frontend is partially live:
  - `/api-health` uses the live API.
  - `/verifications/:id` uses the live API.
  - `/dashboard` is API-backed for verification creation, latest-result review, recent verification records, and counts derived from the current API runtime.
- Verification records are persisted through SQLAlchemy to the configured PostgreSQL database.
- The backend combines deterministic URL heuristics with additional request-time checks such as domain registration age, HTML credential-surface inspection, and TLS transport validation when those lookups succeed.

## Product Overview

Verifiko is positioned as a serious analyst-facing product surface rather than a marketing demo. The project shows how suspicious URLs or content can be reviewed through a clear workflow: assess the target, inspect the contributing signals, understand the reasoning behind the score, review supporting evidence, and decide the next action.

Current web routes:

- `/` product overview
- `/dashboard` verification operations workspace
- `/verifications/:id` verification detail and explainability view
- `/api-health` live API health check

Current API surface:

- `GET /health`
- `POST /api/verifications`
- `GET /api/verifications`
- `GET /api/verifications/{verification_id}`

## Screenshots

Landing page:

![Landing page](/screenshots/landing.png)

Dashboard workspace:

![Dashboard workspace](/screenshots/dashboard.png)

Verification detail view:

![Verification detail view](/screenshots/verification-detail.png)

## Live Demo

Live demo: https://verifiko-demo.example.com

Replace the placeholder URL with the deployed web entry point when the project is published.

## Feature Highlights

- Explainable verification results with readable signal breakdowns
- Analyst-oriented dashboard for triage, evidence review, and next-step framing
- Verification detail surface focused on score rationale, supporting evidence, unresolved items, and recommended action
- Live API health check from the web workspace
- Dashboard overview derived from live verification records in the current API runtime

## Tech Stack

Web:

- React 18
- TypeScript
- Vite
- React Router

API:

- Python 3.11+
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL

## Architecture Overview

The web workspace is a React + TypeScript + Vite application built around reusable layout primitives and a small design system. The API is a FastAPI service with explicit domain, application, infrastructure, and entrypoint layers. The backend verification flow is implemented behind the current API surface, with request-time analyzers for URL heuristics, domain age lookup, HTML credential-surface detection, and TLS validation. Verification records, signals, and risk assessments are now persisted through SQLAlchemy to the configured database. The frontend routes use live API data for health checks, verification detail views, and dashboard record summaries.

## Repository Structure

```text
verifiko/
  api/        FastAPI verification service
  web/        React + TypeScript + Vite investigation workspace
  screenshots/
```

## Running Locally

API:

```bash
cd api
python -m venv .venv
source .venv/bin/activate
cp .env.example .env
pip install -e ".[dev]"
docker compose up -d db
alembic upgrade head
uvicorn app.entrypoints.api.main:app --reload --host 0.0.0.0 --port 8000
```

Web:

```bash
cd web
cp .env.example .env
npm install
npm run dev
```

Web expects the API at `http://localhost:8000` by default.

Production build check:

```bash
cd web
npm run build
```

## Vercel Deployment

Deploy the monorepo as two separate Vercel projects:

- `web/` as the frontend project
- `api/` as the backend project

Recommended order:

1. Create the `api` Vercel project with Root Directory `api/`.
2. Set the required API environment variables:
   - `DATABASE_URL`
   - `CORS_ALLOWED_ORIGINS` for the deployed frontend origin
   - `GOOGLE_CLIENT_ID` with the Google OAuth web client ID used by the frontend
   - `APP_DEBUG=false`
3. Run the migration command against the production database outside the Vercel request runtime:

```bash
cd api
source .venv/bin/activate
DATABASE_URL='YOUR_PRODUCTION_DATABASE_URL' python -m alembic upgrade head
```

4. Deploy the `web` Vercel project with Root Directory `web/`.
5. Set `VITE_API_BASE_URL` in the `web` project to the deployed API base URL.
6. Set `VITE_GOOGLE_CLIENT_ID` in the `web` project to the same Google OAuth web client ID used by the API.

Current deployment-specific behavior:

- The frontend is configured as a Vite SPA and includes a Vercel rewrite for client-side routing.
- The API exposes a Vercel-compatible FastAPI entrypoint from `api/index.py`.
- CORS is environment-driven and does not assume localhost-only origins.
- The frontend refuses to guess a production API URL. `VITE_API_BASE_URL` must be set outside development.
- Google Sign-In requires the same OAuth web client ID in both `GOOGLE_CLIENT_ID` and `VITE_GOOGLE_CLIENT_ID`.

Intentional non-features for the first deployment:

- Alembic migrations are not run during app startup.
- There is no background worker or async job system for verification enrichment.
- There is no authentication or authorization layer yet.

Custom-domain cutover:

1. First deploy both projects on their Vercel-provided domains.
2. Point the frontend project at the deployed API Vercel URL.
3. After end-to-end verification, attach `verifiko.es` to `web` and `api.verifiko.es` to `api`.
4. Update `VITE_API_BASE_URL` to `https://api.verifiko.es`.
5. Update `VITE_GOOGLE_CLIENT_ID` to the production Google OAuth web client ID if it differs from the preview environment.
6. Update `GOOGLE_CLIENT_ID` to the same production Google OAuth web client ID.
7. Update `CORS_ALLOWED_ORIGINS` to `https://verifiko.es`.
8. Add `https://verifiko.es` and the active preview domain origins to the Google OAuth client's Authorized JavaScript origins.

## Testing

Backend tests:

```bash
cd api
source .venv/bin/activate
python -m pytest
```

## Limitations

- Database schema changes are now managed through Alembic migrations and must be applied explicitly before starting the API.
- The dashboard reflects verification records available through the current API surface; it does not provide broader operational telemetry or persistent analyst workflow history beyond those stored verification records.
- Request-time enrichment depends on outbound network access. If RDAP, HTML fetches, or TLS validation fail, the verification still completes with reduced signal coverage.
- Verification creation performs synchronous outbound checks during the request. This is acceptable for a first deployment, but it can add latency and inherits failures from external services.
- There is currently no authentication, authorization, or production-grade operational hardening in the API layer.
