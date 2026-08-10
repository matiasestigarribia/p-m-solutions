"""Stage 2/3 seams exist but are inactive and pull in no heavy dependencies.

Guards the boundary promised in the Kanban spec: future Neon/R2/chatbot code is
isolated behind explicit seams that are NOT imported or required at Stage 1
startup.
"""
import sys

import pytest

from app.core.settings import Settings
from app.services import integrations


def test_seams_report_disabled_by_default():
    s = Settings(_env_file=None)
    assert integrations.database_enabled(s) is False
    assert integrations.object_storage_enabled(s) is False
    assert integrations.chatbot_enabled(s) is False


def test_getting_a_disabled_seam_raises_feature_disabled():
    s = Settings(_env_file=None)
    with pytest.raises(integrations.FeatureDisabled):
        integrations.get_database(s)
    with pytest.raises(integrations.FeatureDisabled):
        integrations.get_object_storage(s)
    with pytest.raises(integrations.FeatureDisabled):
        integrations.get_chatbot(s)


def test_importing_app_does_not_load_deferred_heavy_deps():
    # Importing the whole app must not drag in Stage 2/3 runtime libraries.
    import app.main  # noqa: F401

    for heavy in ("asyncpg", "boto3", "langchain", "pgvector", "sqlalchemy"):
        assert heavy not in sys.modules, f"{heavy} must not be imported at Stage 1 startup"
