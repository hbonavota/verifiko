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
  Limiters **fail open** and use single `EVAL` Lua scripts (1 command each).
- **Deploy**: Vercel — `verifiko-api` (Python API via `api/index.py`) and `verifiko` (frontend).
  Custom domains `api.verifiko.es` / `www.verifiko.es`. DB migrations auto-run via the
  **"DB migrations" GitHub Action** on any push touching `api/alembic/versions/**`.

## How to work here (conventions)

- **Small, low-risk PRs.** One concern per branch, branched from up-to-date `main`.
- **Always run tests + the eval harness** before committing:
  - `cd api && python -m pytest -q`  (full suite; ~410 tests, must stay green)
  - `cd api && python -m evaluation.run_evaluation`  (detection quality — precision **must not**
    regress: baseline precision 1.00, recall ~0.80, FPR 0.00 at MEDIUM threshold)
- **New detection signals** require: enum in `signal_type.py`, weight + category in
  `scoring_policies.py`, EN/ES messages in `domain/i18n/messages.py`, and unit tests.
  Decisive standalone signals are escalated via a compound rule in `compound_rules.py`.
- **Everything risky is behind a feature flag** (settings + env var), off by default, so `main`
  behavior is byte-for-byte unchanged until enabled in Vercel.
- Backend Python here is 3.11 (has `enum.StrEnum`). No shims needed locally.

## Current state (what's merged)

Detection engine: deterministic URL/HTML/TLS heuristics + reputation aggregation (URLhaus +
OpenPhish, 2-of-N consensus, circuit breaker) + parallel waves + Redis caching. SaaS: API keys +
`/api/v1`, async **scan pipeline** (submit → poll/webhook, Postgres job store), **magic-link** auth
(Resend, `login@verifiko.es`), quotas/rate-limits. Recently shipped:

- **Brand typosquatting** detection (`paypa1.com`, `g00gle.com`) — leetspeak + edit-distance.
- **Fail-fast orchestrator** (`VERIFICATION_FAST_PATH_ENABLED`): skips network waves when the
  URL-only verdict is already HIGH/CRITICAL.
- **Phase B.1** — behavioral detonation model: `HeadlessDetonationPort` + `DetonationResult`
  (`app/application/ports/headless_detonation.py`), `BehavioralSignalAnalyzer` (4 signals:
  rendered credential form, offsite form action, JS redirect offsite, drive-by download),
  `DetonationPolicy.should_detonate`.
- **Phase B.2a** — `BrowserlessDetonationClient` adapter (`app/infrastructure/detonation/`,
  Browserless `/function` REST → `DetonationResult`) + `NullHeadlessDetonation` + settings.

## Roadmap — next up

Phase B = headless detonation (dynamic analysis). Full plan in
`docs/PHASE-B-HEADLESS-DETONATION.md`. Locked decisions: **Browserless** (managed `/function`,
with a self-host migration path since it's open-core), **Cloudflare R2** for screenshots,
detonation runs **async-only** (scan pipeline, never on sync `/verifications`).

- **B.2b (next)** — integrate detonation into the pipeline: add `deep_analysis` to
  `CreateVerificationCommand`; on the async scan path, gate with `DetonationPolicy`, run the
  detonation adapter, feed `BehavioralSignalAnalyzer` output into the signals **before scoring**,
  wire in `container.py` behind `DETONATION_ENABLED` (`NullHeadlessDetonation` when off).
  Needs a live Browserless smoke test with a real key. Also validate that the async scan worker
  survives a 10–30s external call on Vercel (`maxDuration`/`waitUntil`), else move the scan worker
  to a small dedicated service.
- **B.3** — screenshot capture + storage in Cloudflare R2; surface `screenshot_ref` in results.
- **B.4** — add detonation-dependent corpus samples; calibrate weights; confirm no regression.
- **Phase C** — computer vision over screenshots (brand-logo match, visual fake-login).
- **Business layer (later)** — usage-based billing (credits, per-request price), domain
  classification product, programmatic SEO (`/domains/*`, threat feed), Chrome extension.

## Gotchas / operational notes

- **Redis is over its Upstash monthly quota**; limiters fail open (limits not enforced) until the
  monthly reset. The EVAL/TTL work cut future usage; watch Upstash usage.
- On Vercel, `VERIFICATION_PARALLEL_ANALYSIS_ENABLED=false` (a DNS EBUSY issue under concurrent
  getaddrinfo). `VERIFICATION_FAST_PATH_ENABLED=true`.
- Resend/Cloudflare: outbound HTTP must send a real browser `User-Agent` or Cloudflare returns
  403 "error 1010" (bit us on the magic-link email; fixed in `resend_email_sender.py`).
- Extended design docs live in `docs/` — read them before large changes.
