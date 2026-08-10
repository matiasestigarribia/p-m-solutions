"""Deferred-integration seams (Stage 2 Neon/R2, Stage 3 chatbot).

These functions are the *only* sanctioned entry points for future integrations.
In Stage 1 every flag is ``False`` and every accessor raises
``FeatureDisabled`` — deliberately, so nothing calls into Neon, Cloudflare R2,
or the chatbot before those stages are authorized.

IMPORTANT: this module imports **no** heavy dependency (asyncpg, SQLAlchemy,
boto3, langchain, pgvector). When a stage is activated, its adapter should be
imported lazily *inside* the corresponding ``get_*`` function so the base
install and Stage 1 startup stay lightweight. ``tests/unit/test_integrations``
enforces this.
"""
from __future__ import annotations


class FeatureDisabled(RuntimeError):
    """Raised when a deferred integration is requested while its flag is off."""


# --- Stage 2: Neon PostgreSQL --------------------------------------------
def database_enabled(settings) -> bool:
    return bool(settings.enable_database)


def get_database(settings):
    """Return a database session factory (Stage 2). Inactive in Stage 1."""
    if not database_enabled(settings):
        raise FeatureDisabled(
            "Database (Neon) is a Stage 2 integration and is disabled. "
            "Set PM_ENABLE_DATABASE=true and provide connection config to activate."
        )
    # Stage 2 seam: lazily import and build the async engine/session here.
    raise NotImplementedError("Stage 2 database adapter not implemented yet.")


# --- Stage 2: Cloudflare R2 object storage -------------------------------
def object_storage_enabled(settings) -> bool:
    return bool(settings.enable_object_storage)


def get_object_storage(settings):
    """Return an object-storage client (Stage 2, Cloudflare R2). Inactive now."""
    if not object_storage_enabled(settings):
        raise FeatureDisabled(
            "Object storage (Cloudflare R2) is a Stage 2 integration and is "
            "disabled. Set PM_ENABLE_OBJECT_STORAGE=true to activate."
        )
    # Stage 2 seam: lazily import boto3 and build the S3-compatible client here.
    raise NotImplementedError("Stage 2 object storage adapter not implemented yet.")


# --- Stage 3: Chatbot -----------------------------------------------------
def chatbot_enabled(settings) -> bool:
    return bool(settings.enable_chatbot)


def get_chatbot(settings):
    """Return the chatbot service (Stage 3). Inactive in Stage 1."""
    if not chatbot_enabled(settings):
        raise FeatureDisabled(
            "Chatbot is a Stage 3 integration and is disabled. "
            "Set PM_ENABLE_CHATBOT=true and provide LLM config to activate."
        )
    # Stage 3 seam: lazily import the RAG/LLM pipeline here.
    raise NotImplementedError("Stage 3 chatbot adapter not implemented yet.")
