# Verifiko

Verifiko is a portfolio-grade verification workspace for suspicious digital content, built to demonstrate explainable scoring, evidence traceability, and operational review workflows.

## Product Overview

Verifiko is positioned as a serious analyst-facing product surface rather than a marketing demo. The project shows how suspicious URLs or content can be reviewed through a clear workflow: assess the target, inspect the contributing signals, understand the reasoning behind the score, review supporting evidence, and decide the next action.

Current frontend routes:

- `/` product overview
- `/dashboard` verification operations workspace
- `/verifications/:id` verification detail and explainability view
- `/api-health` live backend health check

Current backend API:

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

Replace the placeholder URL with the deployed frontend entry point when the project is published.

## Feature Highlights

- Explainable verification results with readable signal breakdowns
- Analyst-oriented dashboard for triage, evidence review, and next-step framing
- Verification detail surface focused on score rationale, supporting evidence, unresolved items, and recommended action
- Live backend health check from the frontend
- Typed demo data used to shape the UI before broader API coupling

## Tech Stack

Frontend:

- React 18
- TypeScript
- Vite
- React Router

Backend:

- Python 3.11+
- FastAPI
- SQLAlchemy scaffolding
- PostgreSQL scaffolding

## Architecture Overview

The frontend is a React + TypeScript + Vite application built around reusable layout primitives and a small design system. The backend is a FastAPI service with clear domain and application layers. The strongest backend logic lives in the verification and scoring flow, while the current UI layer uses typed mock data for dashboard and detail views so the product surface can be shaped cleanly before full live integration.

## Repository Structure

```text
verifiko/
  frontend/   React + TypeScript + Vite application
  backend/    FastAPI service with domain/application core
```

## Running Locally

Backend:

```bash
cd backend
cp .env.example .env
pip install -e .
uvicorn app.entrypoints.api.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Frontend expects the backend at `http://localhost:8000` by default.

Production build check:

```bash
cd frontend
npm run build
```

## Notes For Reviewers

- The frontend is intentionally driven by typed mock data for the dashboard and verification detail routes.
- The backend already exposes a minimal usable API and contains the main domain/application scoring logic.
- Persistent storage and broader backend integrations are intentionally not completed yet.
- The project is intentionally restrained in tone and avoids generic cybersecurity visual cliches.
