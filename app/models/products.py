"""Product — managed content with optional R2-backed media."""
from datetime import datetime

from sqlalchemy import Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    slug: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str] = mapped_column(Text)
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # R2-backed media
    media_url: Mapped[str | None] = mapped_column(nullable=True)
    media_key: Mapped[str | None] = mapped_column(nullable=True)
    display_order: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    def __str__(self) -> str:
        return self.name
