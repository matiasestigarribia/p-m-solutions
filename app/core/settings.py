"""MVP application settings.

All new fields are optional so the app boots in dev with an empty environment.
Production requires a real PM_SECRET_KEY and PM_ENABLE_DATABASE=true with a
PM_DATABASE_URL. R2 credentials are only needed when PM_ENABLE_OBJECT_STORAGE=true.
Product media uses the public media bucket; contact attachments use a separate
private bucket and signed URLs.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_INSECURE_SECRET_KEY = "dev-insecure-change-me"
MIN_PRODUCTION_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Identity -----------------------------------------------------------
    project_name: str = "P & M Solutions"
    version: str = "0.2.0"
    environment: Literal["development", "staging", "production"] = "development"

    # --- CSRF signing -------------------------------------------------------
    secret_key: str = DEV_INSECURE_SECRET_KEY

    # --- Admin JWT (falls back to secret_key if not set) --------------------
    admin_secret_key: Optional[str] = None
    admin_jwt_algorithm: str = "HS256"
    admin_jwt_expiration_minutes: int = 60
    admin_login_rate_limit: int = 5
    admin_login_window_seconds: int = 15 * 60

    # --- Database (Neon PostgreSQL) -----------------------------------------
    enable_database: bool = False
    database_url: Optional[str] = None

    # --- Object storage (Cloudflare R2) -------------------------------------
    enable_object_storage: bool = False
    r2_endpoint_url: Optional[str] = None
    r2_access_key: Optional[str] = None
    r2_secret_key: Optional[str] = None
    r2_bucket_name: Optional[str] = None
    r2_private_bucket_name: Optional[str] = None
    r2_public_url: Optional[str] = None

    # --- Chatbot (never active in MVP) -------------------------------------
    enable_chatbot: bool = False

    # --- Dev contact sink (used only when enable_database=False) -----------
    contact_sink: Literal["logging", "sqlite"] = "sqlite"
    contact_db_path: str = "./data/contact.sqlite3"
    contact_rate_limit_per_hour: int = 20

    @property
    def effective_admin_secret(self) -> str:
        """JWT signing key for admin sessions — falls back to secret_key."""
        return self.admin_secret_key or self.secret_key

    @model_validator(mode="after")
    def _validate(self) -> "Settings":
        if self.environment == "production" and (
            len(self.secret_key.strip()) < MIN_PRODUCTION_SECRET_LENGTH
            or self.secret_key == DEV_INSECURE_SECRET_KEY
        ):
            raise ValueError(
                "PM_SECRET_KEY must contain at least 32 characters and must not "
                "use the development default in production."
            )
        if self.environment == "production" and (
            not self.admin_secret_key
            or len(self.admin_secret_key.strip()) < MIN_PRODUCTION_SECRET_LENGTH
        ):
            raise ValueError(
                "PM_ADMIN_SECRET_KEY must contain at least 32 characters in production."
            )
        if self.environment == "production" and not self.enable_database:
            raise ValueError(
                "PM_ENABLE_DATABASE must be true in production."
            )
        if self.environment == "production" and not self.enable_object_storage:
            raise ValueError(
                "PM_ENABLE_OBJECT_STORAGE must be true in production."
            )
        if self.enable_database and not (self.database_url or "").strip():
            raise ValueError(
                "PM_DATABASE_URL is required when PM_ENABLE_DATABASE=true."
            )
        if self.enable_object_storage and not all([
            self.r2_endpoint_url, self.r2_access_key,
            self.r2_secret_key, self.r2_bucket_name,
            self.r2_private_bucket_name, self.r2_public_url,
        ]):
            raise ValueError(
                "All R2 credentials (PM_R2_ENDPOINT_URL, PM_R2_ACCESS_KEY, "
                "PM_R2_SECRET_KEY, PM_R2_BUCKET_NAME, "
                "PM_R2_PRIVATE_BUCKET_NAME, PM_R2_PUBLIC_URL) are "
                "required when PM_ENABLE_OBJECT_STORAGE=true."
            )
        if (
            self.enable_object_storage
            and self.r2_bucket_name == self.r2_private_bucket_name
        ):
            raise ValueError(
                "PM_R2_BUCKET_NAME and PM_R2_PRIVATE_BUCKET_NAME must be different."
            )
        return self


settings = Settings()
