"""Production must refuse to start with the known dev default (or missing)
``secret_key``. Local development keeps booting with the insecure default.

This guards the audited production blocker: the CSRF signing key in
``app.core.security`` is only as strong as ``secret_key``, so a production
deploy that never overrides ``PM_SECRET_KEY`` would sign tokens with a public,
version-controlled value.
"""
import pytest


DEV_DEFAULT = "dev-insecure-change-me"


def _clear_pm_env(monkeypatch):
    # Ensure no ambient PM_* overrides leak into construction.
    for var in ("PM_ENVIRONMENT", "PM_SECRET_KEY"):
        monkeypatch.delenv(var, raising=False)


def test_production_rejects_default_secret(monkeypatch):
    _clear_pm_env(monkeypatch)
    from app.core.settings import Settings

    with pytest.raises(ValueError):
        Settings(_env_file=None, environment="production", secret_key=DEV_DEFAULT)


def test_production_rejects_missing_secret(monkeypatch):
    # No PM_SECRET_KEY anywhere: the model falls back to the dev default, which
    # is exactly what production must reject.
    _clear_pm_env(monkeypatch)
    from app.core.settings import Settings

    with pytest.raises(ValueError):
        Settings(_env_file=None, environment="production")


def test_production_rejects_empty_secret(monkeypatch):
    _clear_pm_env(monkeypatch)
    from app.core.settings import Settings

    with pytest.raises(ValueError):
        Settings(_env_file=None, environment="production", secret_key="   ")


def test_production_accepts_real_secret(monkeypatch):
    _clear_pm_env(monkeypatch)
    from app.core.settings import Settings

    settings = Settings(
        _env_file=None,
        environment="production",
        secret_key="a-real-strong-production-secret",
    )
    assert settings.environment == "production"
    assert settings.secret_key == "a-real-strong-production-secret"


def test_development_still_boots_with_default_secret(monkeypatch):
    # Local development behavior must be preserved: the insecure default is fine.
    _clear_pm_env(monkeypatch)
    from app.core.settings import Settings

    settings = Settings(_env_file=None)
    assert settings.environment == "development"
    assert settings.secret_key == DEV_DEFAULT
