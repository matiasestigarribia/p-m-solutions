"""Deferred-integration seams.

get_database / get_object_storage / get_chatbot raise FeatureDisabled when
their flag is False. When enabled, they return the real adapter (lazily
imported). get_chatbot always raises — chatbot is absent from MVP.
"""
from __future__ import annotations


class FeatureDisabled(RuntimeError):
    """Raised when a deferred integration is requested while its flag is off."""


# --- Database (Neon PostgreSQL) -------------------------------------------

def database_enabled(settings) -> bool:
    return bool(settings.enable_database)


def get_database(settings):
    """Return get_session generator when database is enabled."""
    if not database_enabled(settings):
        raise FeatureDisabled(
            "Database (Neon) is disabled. "
            "Set PM_ENABLE_DATABASE=true and PM_DATABASE_URL to activate."
        )
    from app.core.database import get_session

    return get_session


# --- Object storage (Cloudflare R2) ---------------------------------------

def object_storage_enabled(settings) -> bool:
    return bool(settings.enable_object_storage)


def get_object_storage(settings):
    """Return upload_to_r2 coroutine when object storage is enabled."""
    if not object_storage_enabled(settings):
        raise FeatureDisabled(
            "Object storage (Cloudflare R2) is disabled. "
            "Set PM_ENABLE_OBJECT_STORAGE=true and R2 credentials to activate."
        )
    from app.services.storage_service import upload_to_r2

    return upload_to_r2


# --- Chatbot (absent from MVP) --------------------------------------------

def chatbot_enabled(settings) -> bool:
    return bool(settings.enable_chatbot)


def get_chatbot(settings):
    """Chatbot is never active in the MVP — always raises FeatureDisabled."""
    if not chatbot_enabled(settings):
        raise FeatureDisabled(
            "Chatbot is a Stage 3 integration and is disabled. "
            "Set PM_ENABLE_CHATBOT=true to activate (not part of MVP)."
        )
    raise NotImplementedError("Chatbot adapter not implemented in MVP.")
