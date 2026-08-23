"""Import all models so Alembic autogenerate can discover them."""
from app.models.base import Base
from app.models.users import User
from app.models.company import Company
from app.models.mission import Mission
from app.models.vision import Vision
from app.models.purpose import Purpose
from app.models.products import Product
from app.models.contact_messages import ContactMessage

__all__ = [
    "Base",
    "User",
    "Company",
    "Mission",
    "Vision",
    "Purpose",
    "Product",
    "ContactMessage",
]
