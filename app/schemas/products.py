"""Product read/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str
    short_description: Optional[str]
    media_url: Optional[str]
    display_order: int
    is_active: bool
    updated_at: datetime
