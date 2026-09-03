"""Import all models so Alembic autogenerate can discover them."""
from app.models.base import Base
from app.models.chat_logs import ChatLog
from app.models.company import Company
from app.models.contact_messages import ContactMessage
from app.models.mission import Mission
from app.models.products import Product
from app.models.purpose import Purpose
from app.models.rag_documents import RagDocument
from app.models.uploaded_documents import UploadedDocument
from app.models.users import User
from app.models.vision import Vision

__all__ = [
    "Base",
    "ChatLog",
    "Company",
    "ContactMessage",
    "Mission",
    "Product",
    "Purpose",
    "RagDocument",
    "UploadedDocument",
    "User",
    "Vision",
]
