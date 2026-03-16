# Verifiko

Verifiko is a portfolio-grade verification workspace for suspicious digital content, built to demonstrate explainable scoring, evidence traceability, and operational review workflows.

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
- Typed demo data used to shape the UI before broader API coupling

## Tech Stack

Web:

- React 18
- TypeScript
- Vite
- React Router

API:

- Python 3.11+
- FastAPI
- SQLAlchemy scaffolding
- PostgreSQL scaffolding

## Architecture Overview

The web workspace is a React + TypeScript + Vite application built around reusable layout primitives and a small design system. The API is a FastAPI service with clear domain and application layers. The strongest API logic lives in the verification and scoring flow, while the current UI layer uses typed mock data for dashboard and detail views so the product surface can be shaped cleanly before full live integration.

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
cp .env.example .env
pip install -e .
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

## Notes For Reviewers

- The web workspace is intentionally driven by typed mock data for the dashboard and verification detail routes.
- The API already exposes a minimal usable service and contains the main domain/application scoring logic.
- Persistent storage and broader API integrations are intentionally not completed yet.
- The project is intentionally restrained in tone and avoids generic cybersecurity visual cliches.
