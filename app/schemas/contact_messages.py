"""ContactMessage DB read schema (separate from the form validation schema)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ContactMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    company: str
    email: str
    phone: str
    location: str
    solution: str
    project_stage: Optional[str]
    need: str
    priority: Optional[str]
    deadline: str
    attachment_url: Optional[str]
    contact_preference: Optional[str]
    best_time: Optional[str]
    is_read: bool
    created_at: datetime
