"""MVP settings must be self-contained: no credentials required to boot.
All deferred integrations (database, R2, chatbot) are optional and disabled by default."""


def test_settings_construct_without_any_secret_env(monkeypatch):
    # Wipe any ambient PM_* overrides that could leak from the environment.
    for var in [
        "PM_DATABASE_URL", "PM_R2_ENDPOINT_URL", "PM_R2_ACCESS_KEY",
        "PM_R2_SECRET_KEY", "PM_R2_BUCKET_NAME", "PM_R2_PUBLIC_URL",
    ]:
        monkeypatch.delenv(var, raising=False)

    from app.core.settings import Settings

    settings = Settings(_env_file=None)

    assert settings.project_name  # has a P&M default
    assert settings.contact_sink in {"logging", "sqlite"}
    # Chatbot configuration is present but remains opt-in and secretless by default.
    assert settings.enable_chatbot is False
    assert settings.groq_api_key is None
    assert "openai_api_key" not in settings.model_dump()
    # MVP fields default to None/False when unset.
    assert settings.database_url is None
    assert settings.r2_bucket_name is None


def test_mvp_flags_disable_deferred_integrations():
    from app.core.settings import Settings

    settings = Settings(_env_file=None)
    # All three deferred integrations are OFF by default.
    assert settings.enable_database is False
    assert settings.enable_object_storage is False
    assert settings.enable_chatbot is False


def test_database_url_normalizes_to_asyncpg():
    from app.core.database import normalize_database_url

    assert normalize_database_url("postgresql://user:pass@host/db") == (
        "postgresql+asyncpg://user:pass@host/db"
    )
    assert normalize_database_url("postgres://user:pass@host/db") == (
        "postgresql+asyncpg://user:pass@host/db"
    )
    assert normalize_database_url(
        "postgresql://user:pass@host/db?sslmode=require&channel_binding=require&application_name=pm"
    ) == (
        "postgresql+asyncpg://user:pass@host/db?ssl=require&application_name=pm"
    )
