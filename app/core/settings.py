"""Stage 1 application settings.

Design constraints (see Sakura notes 03/07/08 and the Stage 1 Kanban spec):

* Settings must be constructible with **no** secret in the environment. Nothing
  here requires Neon, Cloudflare R2, an LLM key, or any other deferred
  integration to build the object.
* The deferred Stage 2 (Neon/R2) and Stage 3 (chatbot) integrations are guarded
  behind boolean feature flags that default to ``False``. Their real
  credentials are intentionally **absent** from this model — they will be read
  by their own optional adapters when, and only when, those flags are enabled.
  Keeping the secrets off the base model is what lets Stage 1 boot with an empty
  environment and is asserted by ``tests/unit/test_settings.py``.
"""
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The insecure local-dev default for ``secret_key``. Booting with this in
# production would sign CSRF tokens with a public, version-controlled value, so
# it (and any blank override) is rejected below when ``environment`` is
# "production".
DEV_INSECURE_SECRET_KEY = "dev-insecure-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Identity -------------------------------------------------------
    project_name: str = "P & M Solutions"
    version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"

    # --- Request signing (CSRF tokens) ----------------------------------
    # A local dev default so the app boots without configuration. MUST be
    # overridden via ``PM_SECRET_KEY`` in any deployed environment.
    secret_key: str = DEV_INSECURE_SECRET_KEY

    # --- Contact form persistence --------------------------------------
    # Stage 1 persists submissions locally behind the ContactSink interface.
    # "sqlite" writes to a local file; "logging" just logs (no storage).
    contact_sink: Literal["logging", "sqlite"] = "sqlite"
    contact_db_path: str = "./data/contact.sqlite3"
    contact_rate_limit_per_hour: int = 20

    # --- Deferred integration seams (inactive in Stage 1) ---------------
    # Stage 2: Neon PostgreSQL. Stage 3: chatbot. Object storage: Cloudflare
    # R2. All OFF by default; no credentials live on this model so Stage 1
    # never needs them to construct or start.
    enable_database: bool = False
    enable_object_storage: bool = False
    enable_chatbot: bool = False

    @model_validator(mode="after")
    def _require_real_secret_in_production(self) -> "Settings":
        # Production must not run on the insecure dev default or a blank key.
        # Development/staging keep booting with the default so local work needs
        # no configuration.
        if self.environment == "production" and (
            not self.secret_key.strip()
            or self.secret_key == DEV_INSECURE_SECRET_KEY
        ):
            raise ValueError(
                "PM_SECRET_KEY must be set to a non-default value when "
                "PM_ENVIRONMENT=production; refusing to start with the insecure "
                "development secret."
            )
        return self


settings = Settings()
