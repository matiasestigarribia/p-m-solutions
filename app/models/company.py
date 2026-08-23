"""Company / Quem Somos — single-row content entity."""
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Company(Base):
    """Stores 'Quem Somos' content. Intended as a single-row table."""

    __tablename__ = "company"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(default="Quem Somos")
    # JSONB list[str] — each element is one paragraph of body copy.
    paragraphs: Mapped[list] = mapped_column(type_=JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    def __str__(self) -> str:
        return self.title
