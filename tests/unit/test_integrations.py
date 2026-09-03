"""Stage 2/3 seams exist but are inactive and pull in no heavy dependencies.

Guards the boundary promised in the Kanban spec: future Neon/R2/chatbot code is
isolated behind explicit seams that are NOT imported or required at Stage 1
startup.
"""
import os
import subprocess
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
    # asyncpg (DB driver), boto3 (R2), and langchain (chatbot) must not be
    # loaded at startup — they are gated behind their enable_* flags.
    # sqlalchemy is a required MVP dep and may be present in sys.modules.
    code = """
import sys
import app.main
for heavy in ("asyncpg", "boto3", "langchain", "pgvector"):
    assert heavy not in sys.modules, f"{heavy} was imported at startup"
"""
    env = os.environ.copy()
    env.update({
        "PM_ENVIRONMENT": "development",
        "PM_ENABLE_DATABASE": "false",
        "PM_ENABLE_OBJECT_STORAGE": "false",
        "PM_ENABLE_CHATBOT": "false",
    })
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
