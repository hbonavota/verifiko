# Proposal

## Why

Two signing secrets ship with hard-coded development defaults and no production check:
the session-token secret (`AUTH_TOKEN_SECRET`) and the scan-webhook signing secret
(`SCAN_WEBHOOK_SIGNING_SECRET`). Once the repository is public, those defaults are known
to everyone. A production deploy that forgets either env var would sign with a public key,
so anyone could forge session tokens or webhook signatures. This is security item S1 and
must land before the repo goes public.

## What Changes

- The API SHALL refuse to start in a production environment when either signing secret is
  still its development default (or blank). The error names the env var(s) to set and
  never prints a secret value.
- "Production" is determined from the declared app environment (`APP_ENV`) and, as a
  backstop, from the hosting platform's production marker (`VERCEL_ENV=production`).
  Today `APP_ENV` defaults to `development` and is not read anywhere, so it alone could
  leave the guard inactive on Vercel.
- Development and test environments keep the current defaults, so local runs and the test
  suite need no new configuration.
- **BREAKING (deploy-time only)**: a production deploy without real values for both
  secrets now fails at startup instead of silently running with forgeable keys.

## Capabilities

### New Capabilities

- `production-config-safety`: startup-time checks that refuse to run a production
  deployment with unsafe configuration. Starts with the signing-secret check and can hold
  future production-only config checks.

### Modified Capabilities

None.

## Impact

- Code: `api/app/infrastructure/config/settings.py` (startup validation, named dev-default
  constants, the platform environment field). New unit test under
  `api/tests/unit/infrastructure/`.
- Runtime: the check runs when settings are first loaded. That happens at import in
  `app/entrypoints/api/main.py`, so a misconfigured production deploy fails its cold start.
- Ops: before merging, the `verifiko-api` Vercel project must have real values for
  `AUTH_TOKEN_SECRET` and `SCAN_WEBHOOK_SIGNING_SECRET` in Production (manual check).
- No API, schema, migration, or frontend changes. The migrations workflow is unaffected:
  it sets `DATABASE_URL`, so Alembic does not load settings.
