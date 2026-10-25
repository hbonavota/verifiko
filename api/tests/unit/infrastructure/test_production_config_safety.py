"""Production refuses to start with the public development signing secrets.

The dev defaults for AUTH_TOKEN_SECRET / SCAN_WEBHOOK_SIGNING_SECRET live in a
public repo, so a production deploy that forgets either env var would sign
session tokens or webhooks with a key anyone can read. ``Settings`` fails closed
in production; development and test keep the defaults.
"""

import pytest
from pydantic import ValidationError

from app.infrastructure.config.settings import (
    _DEV_AUTH_TOKEN_SECRET,
    _DEV_WEBHOOK_SIGNING_SECRET,
    Settings,
)

REAL_AUTH_SECRET = "real-auth-secret-0123456789"
REAL_WEBHOOK_SECRET = "real-webhook-secret-0123456789"


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "APP_ENV",
        "VERCEL_ENV",
        "AUTH_TOKEN_SECRET",
        "SCAN_WEBHOOK_SIGNING_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)


def _settings(**overrides: str) -> Settings:
    # _env_file=None: a developer's local .env must never flip these tests.
    return Settings(_env_file=None, **overrides)


def test_production_rejects_default_auth_token_secret() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _settings(app_env="production", scan_webhook_signing_secret=REAL_WEBHOOK_SECRET)

    message = str(exc_info.value)
    assert "AUTH_TOKEN_SECRET" in message
    assert "SCAN_WEBHOOK_SIGNING_SECRET" not in message


def test_production_rejects_default_webhook_signing_secret() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _settings(app_env="production", auth_token_secret=REAL_AUTH_SECRET)

    message = str(exc_info.value)
    assert "SCAN_WEBHOOK_SIGNING_SECRET" in message
    assert "AUTH_TOKEN_SECRET" not in message


def test_production_names_both_secrets_in_one_error() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _settings(app_env="production")

    assert len(exc_info.value.errors()) == 1
    message = str(exc_info.value)
    assert "AUTH_TOKEN_SECRET" in message
    assert "SCAN_WEBHOOK_SIGNING_SECRET" in message


@pytest.mark.parametrize("blank", ["", "   "])
def test_production_rejects_blank_secret(blank: str) -> None:
    with pytest.raises(ValidationError, match="AUTH_TOKEN_SECRET"):
        _settings(
            app_env="production",
            auth_token_secret=blank,
            scan_webhook_signing_secret=REAL_WEBHOOK_SECRET,
        )


def test_error_never_contains_secret_values() -> None:
    # One secret real, one default: neither value may reach the startup logs.
    with pytest.raises(ValidationError) as exc_info:
        _settings(app_env="production", scan_webhook_signing_secret=REAL_WEBHOOK_SECRET)

    message = str(exc_info.value)
    assert _DEV_AUTH_TOKEN_SECRET not in message
    assert _DEV_WEBHOOK_SIGNING_SECRET not in message
    assert REAL_WEBHOOK_SECRET not in message
    assert REAL_WEBHOOK_SECRET[-12:] not in message


def test_production_starts_with_both_secrets_overridden() -> None:
    settings = _settings(
        app_env="production",
        auth_token_secret=REAL_AUTH_SECRET,
        scan_webhook_signing_secret=REAL_WEBHOOK_SECRET,
    )

    assert settings.is_production
    assert settings.auth_token_secret == REAL_AUTH_SECRET


@pytest.mark.parametrize("app_env", ["staging", "prod", "Production", "  PRODUCTION "])
def test_unrecognized_environment_fails_closed(app_env: str) -> None:
    with pytest.raises(ValidationError, match="AUTH_TOKEN_SECRET"):
        _settings(app_env=app_env)


@pytest.mark.parametrize("app_env", [None, "development"])
def test_vercel_production_overrides_declared_environment(
    monkeypatch: pytest.MonkeyPatch, app_env: str | None
) -> None:
    monkeypatch.setenv("VERCEL_ENV", "production")
    if app_env is not None:
        monkeypatch.setenv("APP_ENV", app_env)

    with pytest.raises(ValidationError, match="SCAN_WEBHOOK_SIGNING_SECRET"):
        _settings()


def test_secrets_are_read_from_environment_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("AUTH_TOKEN_SECRET", REAL_AUTH_SECRET)
    monkeypatch.setenv("SCAN_WEBHOOK_SIGNING_SECRET", REAL_WEBHOOK_SECRET)

    settings = _settings()

    assert settings.is_production
    assert settings.scan_webhook_signing_secret == REAL_WEBHOOK_SECRET


@pytest.mark.parametrize(
    "app_env", [None, "development", "dev", "local", "test", "TEST"]
)
def test_non_production_keeps_dev_defaults(
    monkeypatch: pytest.MonkeyPatch, app_env: str | None
) -> None:
    if app_env is not None:
        monkeypatch.setenv("APP_ENV", app_env)

    settings = _settings()

    assert not settings.is_production
    assert settings.auth_token_secret == _DEV_AUTH_TOKEN_SECRET
    assert settings.scan_webhook_signing_secret == _DEV_WEBHOOK_SIGNING_SECRET


@pytest.mark.parametrize("vercel_env", ["preview", "development"])
def test_vercel_non_production_follows_app_env(
    monkeypatch: pytest.MonkeyPatch, vercel_env: str
) -> None:
    monkeypatch.setenv("VERCEL_ENV", vercel_env)

    assert not _settings().is_production
