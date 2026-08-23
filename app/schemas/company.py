"""Read schemas for the single-row content entities."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ContentEntityOut(BaseModel):
    """Shared shape for Company / Mission / Vision / Purpose."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    paragraphs: list[str]
    updated_at: datetime


class CompanyOut(ContentEntityOut):
    pass


class MissionOut(ContentEntityOut):
    pass


class VisionOut(ContentEntityOut):
    pass


class PurposeOut(ContentEntityOut):
    pass
