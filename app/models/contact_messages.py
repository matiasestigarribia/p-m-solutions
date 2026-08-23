"""ContactMessage — persists full contact form qualification data.

Mirrors the ContactSubmission schema fields plus admin-facing fields
(is_read) and optional R2 attachment metadata.
"""
from datetime import datetime

from sqlalchemy import Boolean, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Contact info
    full_name: Mapped[str]
    company: Mapped[str] = mapped_column(default="")
    email: Mapped[str]
    phone: Mapped[str]
    location: Mapped[str] = mapped_column(default="")

    # Project qualification
    solution: Mapped[str]
    project_stage: Mapped[str | None] = mapped_column(nullable=True)
    need: Mapped[str] = mapped_column(Text)
    priority: Mapped[str | None] = mapped_column(nullable=True)
    deadline: Mapped[str] = mapped_column(default="")

    # Optional R2 attachment
    attachment_url: Mapped[str | None] = mapped_column(nullable=True)
    attachment_key: Mapped[str | None] = mapped_column(nullable=True)

    # Scheduling preference
    contact_preference: Mapped[str | None] = mapped_column(nullable=True)
    best_time: Mapped[str | None] = mapped_column(nullable=True)

    # Admin
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"
