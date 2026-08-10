"""Stage 1 settings must be self-contained: no Neon/R2/LLM secret is required
to construct Settings. Any deferred integration is optional and disabled."""
import os


def test_settings_construct_without_any_secret_env(monkeypatch):
    # Wipe every deferred-integration variable the reference baseline required.
    for var in [
        "DATABASE_URL", "JWT_SECRET_KEY", "JWT_ALGORITHM", "JWT_EXPIRATION_MINUTES",
        "OPENAI_API_KEY", "GROQ_API_KEY", "PRIMARY_LLM", "BACKUP_LLM",
        "EMBEDDING_MODEL", "R2_ENDPOINT_URL", "R2_ACCESS_KEY", "R2_SECRET_KEY",
        "R2_BUCKET_NAME", "R2_PUBLIC_URL",
    ]:
        monkeypatch.delenv(var, raising=False)

    from app.core.settings import Settings

    settings = Settings(_env_file=None)

    assert settings.project_name  # has a P&M default
    assert settings.contact_sink in {"logging", "sqlite"}
    # No attribute should surface a Neon/R2/LLM secret in Stage 1.
    banned = {"database_url", "openai_api_key", "r2_bucket_name", "groq_api_key"}
    assert banned.isdisjoint(set(settings.model_dump().keys()))


def test_stage1_flags_disable_deferred_integrations():
    from app.core.settings import Settings

    settings = Settings(_env_file=None)
    # Stage 2/3 features are OFF by default and never instantiated at import time.
    assert settings.enable_database is False
    assert settings.enable_object_storage is False
    assert settings.enable_chatbot is False
