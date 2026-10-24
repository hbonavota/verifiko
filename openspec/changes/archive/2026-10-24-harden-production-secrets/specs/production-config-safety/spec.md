# Spec Delta

## Purpose

Prevent a production deployment of the API from running with unsafe, publicly known
configuration. The service checks its configuration at startup and refuses to run in
production with values that are only meant for local development.

## ADDED Requirements

### Requirement: Production refuses development signing secrets
In a production environment, the service SHALL refuse to start if the session-token
signing secret (`AUTH_TOKEN_SECRET`) or the scan-webhook signing secret
(`SCAN_WEBHOOK_SIGNING_SECRET`) still has its built-in development default or is blank.
The startup error SHALL name every offending env var and SHALL NOT include any secret
value.

#### Scenario: Session-token secret left at its default
- **WHEN** the service starts in production with `SCAN_WEBHOOK_SIGNING_SECRET` set to a real value and `AUTH_TOKEN_SECRET` unset
- **THEN** startup fails with an error that names `AUTH_TOKEN_SECRET`
- **AND** the error does not contain the development default value

#### Scenario: Webhook signing secret left at its default
- **WHEN** the service starts in production with `AUTH_TOKEN_SECRET` set to a real value and `SCAN_WEBHOOK_SIGNING_SECRET` unset
- **THEN** startup fails with an error that names `SCAN_WEBHOOK_SIGNING_SECRET`

#### Scenario: Both secrets left at their defaults
- **WHEN** the service starts in production with neither secret set
- **THEN** startup fails with a single error that names both `AUTH_TOKEN_SECRET` and `SCAN_WEBHOOK_SIGNING_SECRET`

#### Scenario: Secret set to a blank value
- **WHEN** the service starts in production with `AUTH_TOKEN_SECRET` set to an empty or whitespace-only string
- **THEN** startup fails with an error that names `AUTH_TOKEN_SECRET`

#### Scenario: Both secrets overridden
- **WHEN** the service starts in production with both secrets set to non-default, non-blank values
- **THEN** the service starts normally

### Requirement: Production environment detection
The service SHALL treat itself as production unless the declared app environment
(`APP_ENV`, `development` when unset) is a recognized non-production value
(`development`, `dev`, `local`, `test`, case-insensitive). It SHALL also treat itself as production whenever the hosting platform
reports a production deployment (`VERCEL_ENV=production`), whatever `APP_ENV` says.

#### Scenario: Declared production
- **WHEN** `APP_ENV` is `production` and `VERCEL_ENV` is unset
- **THEN** the production configuration checks apply

#### Scenario: Unrecognized environment name fails closed
- **WHEN** `APP_ENV` is a value outside the recognized non-production set (for example `staging` or `prod`)
- **THEN** the production configuration checks apply

#### Scenario: Platform production marker overrides the declared environment
- **WHEN** `VERCEL_ENV` is `production` and `APP_ENV` is unset or `development`
- **THEN** the production configuration checks apply

### Requirement: Development and test keep working defaults
In a non-production environment, the service SHALL start with the built-in development
signing secrets, so local runs and the automated test suite need no extra configuration.

#### Scenario: Local development with defaults
- **WHEN** `APP_ENV` is `development` (or unset), `VERCEL_ENV` is not `production`, and neither secret is set
- **THEN** the service starts normally using the development defaults

#### Scenario: Test environment with defaults
- **WHEN** `APP_ENV` is `test` and neither secret is set
- **THEN** the service starts normally
