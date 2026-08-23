"""Test-process isolation from the deployment .env file."""
from __future__ import annotations

import os

# The repository lives beside a real production .env on the VPS. Tests must
# never import the application with production integrations enabled.
os.environ["PM_ENVIRONMENT"] = "development"
os.environ["PM_ENABLE_DATABASE"] = "false"
os.environ["PM_ENABLE_OBJECT_STORAGE"] = "false"
