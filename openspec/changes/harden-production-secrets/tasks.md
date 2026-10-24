# Tasks

## 1. Startup validation in Settings

- [x] 1.1 In `api/app/infrastructure/config/settings.py`, add module constants `_DEV_AUTH_TOKEN_SECRET` / `_DEV_WEBHOOK_SIGNING_SECRET` and use them as the field defaults (values unchanged); verify with `git diff` that defaults are byte-identical
- [x] 1.2 Add field `vercel_env: str = ""` and a production check (`app_env.strip().lower()` not in `{"development", "dev", "local", "test"}` OR `vercel_env.strip().lower() == "production"`); verify via the tests in 1.4
- [x] 1.3 Add `@model_validator(mode="after")` that, in production, collects each signing secret equal to its dev default or blank and raises one `ValueError` naming the env vars (`field.upper()`) and how to fix, without any secret value; verify via the tests in 1.4
- [x] 1.4 Add `api/tests/unit/infrastructure/test_production_config_safety.py` (builds `Settings(_env_file=None, ...)` after `monkeypatch.delenv` of `APP_ENV`, `VERCEL_ENV`, `AUTH_TOKEN_SECRET`, `SCAN_WEBHOOK_SIGNING_SECRET`) covering every spec scenario: each secret at default raises and names its var; both at default names both; blank raises; message never contains either dev default; both overridden starts; `staging`/`prod` fail closed; `VERCEL_ENV=production` overrides `APP_ENV=development` (via `setenv`); `development`/unset and `test` with defaults start. Verify with `cd api && python -m pytest -q tests/unit/infrastructure/test_production_config_safety.py`

## 2. Regression checks

- [x] 2.1 Run the full suite `cd api && python -m pytest -q` and verify it is green with no new config (the suite must not depend on `APP_ENV`/`VERCEL_ENV`)
- [x] 2.2 Run `cd api && python -m evaluation.run_evaluation` and verify precision 1.00 / FPR 0.00 at MEDIUM, recall unchanged (~0.80)
- [x] 2.3 Verify `openspec validate harden-production-secrets --strict` passes and the diff touches only `settings.py`, the new test, and this change's artifacts (no frontend)
