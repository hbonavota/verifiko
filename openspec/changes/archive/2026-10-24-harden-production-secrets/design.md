# Design

## Context

- `Settings` (`api/app/infrastructure/config/settings.py`) is a pydantic-settings
  `BaseSettings`. Each field reads the env var of the same name, upper-cased. It also reads
  an optional `.env` file.
- `scan_webhook_signing_secret` defaults to `"verifiko-dev-webhook-secret"` and
  `auth_token_secret` defaults to `"verifiko-dev-auth-secret"`. The only places that read
  them are `container.py` (token service, webhook notifier).
- `app_env` exists (default `"development"`) but nothing reads it today. Whether
  `APP_ENV` is set in the Vercel `verifiko-api` project is unknown.
- `get_settings()` is `@lru_cache`d and first runs at import in
  `app/entrypoints/api/main.py`. `api/index.py` imports that module for Vercel, so a
  validation error there fails the function's cold start. `lru_cache` does not cache
  exceptions, so each new instance would fail the same way.
- Alembic `env.py` calls `get_settings()` only when `DATABASE_URL` is unset. The
  migrations workflow sets it, so migrations never run this check.
- Integration tests already `monkeypatch.setenv("AUTH_TOKEN_SECRET", ...)`. No test sets
  `APP_ENV` or `VERCEL_ENV`.

## Goals / Non-Goals

**Goals:**
- Fail closed: an unknown or misspelled environment name counts as production.
- Validate once, at settings construction, and report every offending var in one error.

**Non-Goals:**
- Secret strength rules (minimum length, entropy). Only "default or blank" is rejected.
- Other secrets that default to empty (`RESEND_API_KEY`, QStash keys, R2 keys). They fail
  safe or are feature-flagged, so they are out of scope for S1.
- Guarding Vercel Preview deployments. They follow `APP_ENV` (see Decisions).
- Rotating the secrets currently in production, or editing the untracked
  `api/.env.example`.

## Decisions

1. **Validate with a `@model_validator(mode="after")` on `Settings`.** It runs on every
   construction, wherever settings come from (env, `.env`, kwargs). That covers the app
   and the tests with one code path. Alternative: check in a FastAPI startup or lifespan
   hook. Rejected because it only covers the HTTP app and fires after import, while
   anything else that builds settings would skip it.

2. **Production = `app_env` not in the dev allowlist, OR `vercel_env == "production"`.**
   - Allowlist `{"development", "dev", "local", "test"}`, compared after `strip().lower()`.
     Anything else (`production`, `prod`, `staging`, a typo) counts as production.
     Alternative: a production denylist (`== "production"`). Rejected because a typo
     would silently skip the guard.
   - Add field `vercel_env: str = ""`. pydantic-settings fills it from `VERCEL_ENV`, which
     Vercel sets automatically to `production`, `preview`, or `development`. This is the
     backstop for an `APP_ENV` that is unset in Vercel. Without it, the default
     `app_env="development"` would turn the guard off in exactly the deploy it exists for.
     Alternative: change the `app_env` default to `production`. Rejected because it breaks
     local DX and every test that builds `Settings()`.
   - Preview (`VERCEL_ENV=preview`) is not forced to production. Previews may run on dev
     defaults today, and forcing them would break PR previews, which is a separate
     decision. If `APP_ENV=production` is set for Preview, the guard still applies.

3. **Named module constants** `_DEV_AUTH_TOKEN_SECRET` and `_DEV_WEBHOOK_SIGNING_SECRET`
   serve as both the field defaults and the comparison values, so the strings are not
   repeated. Blank (`not value.strip()`) is rejected along with the default because an
   empty HMAC key is just as forgeable.

4. **Error shape.** Raise `ValueError` from the validator, which pydantic wraps in a
   `ValidationError` at `Settings()`. The message lists the env var names
   (`AUTH_TOKEN_SECRET`, `SCAN_WEBHOOK_SIGNING_SECRET`), says why, and says what to do:
   set a unique random value. It never includes a field value. The env var name is built
   from the field name (`name.upper()`), so it always matches what pydantic-settings reads.
   `model_config` sets `hide_input_in_errors=True`. Without it, pydantic appends a
   truncated `input_value=` repr of the whole input to the error, which leaked the tail of
   whichever secret *was* set (found while implementing). It also keeps any other settings
   error from echoing env values such as `DATABASE_URL` into logs.

5. **Tests build `Settings` directly with `_env_file=None`** and `monkeypatch.delenv` for
   `APP_ENV`, `VERCEL_ENV`, and the two secrets. A developer's local `.env` or shell can
   then never flip a test. Production is selected through kwargs or `setenv`, which also
   proves the env var path works.

## Risks / Trade-offs

- [Vercel Production is missing one of the vars] → the deploy fails at cold start (every
  request returns 500). This is the intended fail-closed behavior. Mitigation: the manual
  pre-merge check of both vars in `verifiko-api` → Production. Rollback is reverting the
  merge or setting the var and redeploying.
- [`VERCEL_ENV=production` set by hand in a local shell] → local startup fails with the
  clear error. That is acceptable and easy to fix.
- [A test elsewhere builds `Settings(app_env="production")` with defaults] → it would now
  raise. None exist today (grep). The full suite run in tasks confirms it.

## Migration Plan

1. Confirm in Vercel (`verifiko-api` → Settings → Environment Variables → Production) that
   `AUTH_TOKEN_SECRET` and `SCAN_WEBHOOK_SIGNING_SECRET` have real values (manual, owner).
2. Merge. The Vercel deploy picks up the change. Smoke test: `GET` any API route returns
   non-5xx.
3. Rollback: revert the PR, or set the missing var and redeploy. No data or schema state
   is involved.
