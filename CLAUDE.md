# Verifiko — project context for Claude Code

Verifiko is a portfolio-grade SaaS for **URL reputation / phishing & malware detection**.
Public product ("Is this link safe?") + a developer API. Direct competitor and model to
beat: **URLert** (see `docs/COMPETITIVE-ANALYSIS-URLERT.md`).

## Stack & layout

- **Backend** (`api/`): FastAPI, **Clean Architecture** — strict layering:
  - `app/domain` — entities, value objects, enums, domain services, ports (interfaces). No I/O.
  - `app/application` — use cases, DTOs, mappers, application services (signal analyzers), ports.
  - `app/infrastructure` — adapters (persistence, security, email, detonation, cache, reputation…).
  - `app/entrypoints/api` — FastAPI routes, schemas, and the DI `container.py`.
  - Dependency injection is `container.py` with `@lru_cache` provider functions.
- **Frontend** (`web/`): React + Vite + TypeScript. Styles in `web/src/styles/*.css`. i18n EN/ES.
- **DB**: Neon (Postgres) via SQLAlchemy + Alembic (`api/alembic/versions`). Driver is **psycopg v3**
  — URLs must be normalized to `postgresql+psycopg://` (see `normalize_database_url`).
- **Redis**: Upstash (`REDIS_URL`, `rediss://`). Used for rate/quota limiters and caches.
  Limiters use single `EVAL` Lua scripts (1 command each).
- **Deploy**: Vercel — `verifiko-api` (Python API via `api/index.py`) and `verifiko` (frontend).
  Custom domains `api.verifiko.es` / `www.verifiko.es`. DB migrations auto-run via the
  **"DB migrations" GitHub Action** on any push touching `api/alembic/versions/**`.

## How to work here (conventions)

- **Small, low-risk PRs.** One concern per branch, branched from up-to-date `main`.
- **Always run tests + the eval harness** before committing:
  - `cd api && python -m pytest -q`  (full suite; ~500 tests, must stay green)
  - `cd api && python -m evaluation.run_evaluation`  (detection quality — precision **must not**
    regress: baseline precision 1.00, recall ~0.80, FPR 0.00 at MEDIUM threshold)
  - `cd web && npm run test`  (Vitest + Testing Library; test files sit next to the code as
    `*.test.{ts,tsx}`, with explicit imports from `vitest`, no globals)
  - `cd api && ruff check . && black --check .`  (lint + format; `black .` and
    `ruff check --fix .` apply fixes. Alembic migrations are excluded.)
- **New detection signals** require: enum in `signal_type.py`, weight + category in
  `scoring_policies.py`, EN/ES messages in `domain/i18n/messages.py`, and unit tests.
  Decisive standalone signals are escalated via a compound rule in `compound_rules.py`.
- **Everything risky is behind a feature flag** (settings + env var), off by default, so `main`
  behavior is byte-for-byte unchanged until enabled in Vercel.
- Backend requires Python ≥ 3.11 (`requires-python`, uses `enum.StrEnum`); local dev and the
  migrations workflow use 3.11, `api/.python-version` pins 3.12. No shims needed.
- **Behavior changes go through OpenSpec** (`/opsx:propose` → `/opsx:apply` → `/opsx:archive`);
  living specs are in `openspec/specs/`. Docs, refactors and dependency hygiene skip it.

## Current state (what's merged)

Detection engine: deterministic URL/HTML/TLS heuristics + reputation aggregation (URLhaus +
OpenPhish, 2-of-N consensus, circuit breaker) + wave-based orchestration + Redis caching +
multi-user-agent anti-cloaking (`CONTENT_VARIATION_DETECTED`). SaaS: API keys + `/api/v1`, async
**scan pipeline** (submit/batch → poll/webhook, Postgres job store; in-process or QStash dispatch
via `SCAN_DISPATCH_MODE`), auth via **Google Sign-In**, **magic link** (Resend) and email +
password (Argon2), quotas/rate-limits. Also shipped:

- **Brand typosquatting** detection (`paypa1.com`, `g00gle.com`) — leetspeak + edit-distance.
- **Fail-fast orchestrator** (`VERIFICATION_FAST_PATH_ENABLED`): skips network waves when the
  URL-only verdict is already HIGH/CRITICAL.
- **Phase B — headless detonation ("deep scan"), behind flags.** Plan and locked decisions in
  `docs/PHASE-B-HEADLESS-DETONATION.md`: **Browserless** (managed `/function`, self-host path),
  **Cloudflare R2** for screenshots, detonation **async-only** (scan pipeline, never on sync
  `/verifications`).
  - **B.1** — `HeadlessDetonationPort` + `DetonationResult`, `BehavioralSignalAnalyzer` (rendered
    credential form, offsite form action, JS redirect offsite, drive-by download),
    `DetonationPolicy.should_detonate`.
  - **B.2a** — `BrowserlessDetonationClient` adapter + `NullHeadlessDetonation`.
  - **B.2b** — pipeline integration: `deep_analysis` on `CreateVerificationCommand` (set by the
    scan processor), gated by `DetonationPolicy`; behavioral signals are merged **before
    scoring**; wired in `container.py` behind `DETONATION_ENABLED`.
  - **B.3** — screenshots stored in R2 (`R2ScreenshotStore`, `SCREENSHOT_STORAGE_ENABLED`); only
    the object key (`screenshot_ref`) travels through the pipeline, and responses expose a
    presigned `screenshot_url`. Plan in `docs/PHASE-B3-SCREENSHOTS-R2.md`.
  - Web: deep-scan toggle for signed-in users + screenshot lightbox on the result/detail views.
- **Production config safety**: the API refuses to start in production with a dev/blank
  `AUTH_TOKEN_SECRET` or `SCAN_WEBHOOK_SIGNING_SECRET` (spec `production-config-safety`).
- Web: PWA (behind `VITE_PWA_ENABLED`), build-time prerendered landing.

## Roadmap — next up

- **B.4** — add detonation-dependent corpus samples; calibrate weights; confirm no regression.
- **Phase C** — computer vision over screenshots (brand-logo match, visual fake-login).
- **Business layer (later)** — usage-based billing (credits, per-request price), domain
  classification product, programmatic SEO (`/domains/*`, threat feed), Chrome extension.
- A CI workflow for the API and web test suites and the eval harness.

## Conventions worth knowing

- Outbound requests to user-controlled destinations (verification targets, redirects, webhooks)
  must go through the outbound target guard and the pinned HTTP client — see
  `openspec/specs/outbound-fetch-guard/spec.md`.
- Extended design docs live in `docs/` — read them before large changes.
