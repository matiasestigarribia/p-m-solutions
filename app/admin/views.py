"""SQLAdmin ModelViews for all P&M entities."""
from __future__ import annotations

from typing import ClassVar

from sqladmin import ModelView
from wtforms import FileField

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


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-users"
    can_delete = True

    column_list = [User.id, User.username, User.email, User.created_at]
    column_searchable_list = [User.username, User.email]
    form_excluded_columns = [User.created_at, User.updated_at]

    async def on_model_change(self, data, model, is_created, request):
        from app.core.security import get_password_hash

        value = data.get("password", "")
        if value and not value.startswith("$argon2"):
            data["password"] = get_password_hash(value)
        elif not value and not is_created:
            if "password" in data:
                del data["password"]


class CompanyAdmin(ModelView, model=Company):
    name = "Company"
    name_plural = "Company (Quem Somos)"
    icon = "fa-solid fa-building"
    can_delete = True

    column_list = [Company.id, Company.title, Company.updated_at]
    form_excluded_columns = [Company.created_at, Company.updated_at]
    form_widget_args = {"paragraphs": {"rows": 10}}


class MissionAdmin(ModelView, model=Mission):
    name = "Mission"
    name_plural = "Mission"
    icon = "fa-solid fa-bullseye"
    can_delete = True

    column_list = [Mission.id, Mission.title, Mission.updated_at]
    form_excluded_columns = [Mission.created_at, Mission.updated_at]
    form_widget_args = {"paragraphs": {"rows": 6}}


class VisionAdmin(ModelView, model=Vision):
    name = "Vision"
    name_plural = "Vision"
    icon = "fa-solid fa-eye"
    can_delete = True

    column_list = [Vision.id, Vision.title, Vision.updated_at]
    form_excluded_columns = [Vision.created_at, Vision.updated_at]
    form_widget_args = {"paragraphs": {"rows": 6}}


class PurposeAdmin(ModelView, model=Purpose):
    name = "Purpose"
    name_plural = "Purpose (Propósito)"
    icon = "fa-solid fa-star"
    can_delete = True

    column_list = [Purpose.id, Purpose.title, Purpose.updated_at]
    form_excluded_columns = [Purpose.created_at, Purpose.updated_at]
    form_widget_args = {"paragraphs": {"rows": 8}}


class ProductAdmin(ModelView, model=Product):
    name = "Product"
    name_plural = "Products"
    icon = "fa-solid fa-box"
    can_delete = True

    column_list = [
        Product.id, Product.name, Product.slug, Product.is_active,
        Product.display_order, Product.updated_at,
    ]
    form_overrides = {"media_url": FileField}
    form_create_rules = [
        "name", "slug", "description", "short_description",
        "media_url", "display_order", "is_active",
    ]
    form_edit_rules = [
        "name", "slug", "description", "short_description",
        "media_url", "display_order", "is_active",
    ]
    form_widget_args = {
        "description": {"rows": 8},
        "short_description": {"rows": 4},
    }
    form_excluded_columns = [Product.created_at, Product.updated_at, Product.media_key]

    async def on_model_change(self, data, model, is_created, request):
        value = data.get("media_url")

        if value is None or isinstance(value, str):
            return

        if not hasattr(value, "read"):
            return

        from app.core.settings import settings

        if not settings.enable_object_storage:
            data["media_url"] = None
            return

        from app.services.image_service import optimize_image_bytes
        from app.services.storage_service import (
            ALLOWED_IMAGE_TYPES,
            MAX_IMAGE_BYTES,
            upload_to_r2,
            validate_upload_content,
        )

        content_type = getattr(value, "content_type", None) or ""
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError("Only JPEG, PNG, GIF, or WebP product images are allowed.")
        content = await value.read(MAX_IMAGE_BYTES + 1)
        if len(content) > MAX_IMAGE_BYTES:
            raise ValueError("Product image exceeds the 10 MB limit.")
        if not content:
            data["media_url"] = None
            return
        validate_upload_content(content, content_type)

        webp_bytes, new_filename = await optimize_image_bytes(value, content)
        public_url, key = await upload_to_r2(
            file_bytes=webp_bytes,
            folder="products",
            filename=new_filename,
            content_type="image/webp",
        )
        data["media_url"] = public_url
        data["media_key"] = key


class ContactMessageAdmin(ModelView, model=ContactMessage):
    name = "Contact Message"
    name_plural = "Contact Messages"
    icon = "fa-solid fa-envelope"
    can_delete = True

    column_list = [
        ContactMessage.id,
        ContactMessage.full_name,
        ContactMessage.email,
        ContactMessage.solution,
        ContactMessage.is_read,
        ContactMessage.created_at,
    ]
    column_searchable_list = [ContactMessage.full_name, ContactMessage.email]
    form_excluded_columns = [
        ContactMessage.created_at,
        ContactMessage.updated_at,
        ContactMessage.attachment_key,
    ]
    form_widget_args = {"need": {"rows": 6}}


class RagDocumentAdmin(ModelView, model=RagDocument):
    name = "RAG Chunk"
    name_plural = "RAG Chunks"
    icon = "fa-solid fa-database"
    can_create = False
    can_edit = False
    can_delete = True
    column_list: ClassVar = [RagDocument.id, RagDocument.source, RagDocument.language, RagDocument.active, RagDocument.created_at]


class ChatLogAdmin(ModelView, model=ChatLog):
    name = "Chat Log"
    name_plural = "Chat Logs"
    icon = "fa-solid fa-comments"
    can_create = False
    can_edit = False
    can_delete = True
    column_list: ClassVar = [ChatLog.id, ChatLog.user_message, ChatLog.bot_reply, ChatLog.language, ChatLog.created_at]


class UploadedDocumentAdmin(ModelView, model=UploadedDocument):
    name = "RAG Upload"
    name_plural = "RAG Uploads"
    icon = "fa-solid fa-file-arrow-up"
    can_delete = True
    form_overrides: ClassVar = {"file_path": FileField}
    form_create_rules: ClassVar = ["filename", "file_path", "language"]
    form_edit_rules: ClassVar = ["filename", "language"]
    column_list: ClassVar = [UploadedDocument.id, UploadedDocument.filename, UploadedDocument.language, UploadedDocument.created_at]

    async def on_model_change(self, data, model, is_created, request):
        from starlette.datastructures import UploadFile

        upload = data.get("file_path")
        if not isinstance(upload, UploadFile):
            return
        content = await upload.read()
        if not content:
            raise ValueError("Choose a PDF, Markdown, or TXT document.")
        filename = upload.filename or "knowledge.txt"
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        content_types = {"pdf": "application/pdf", "md": "text/markdown", "txt": "text/plain"}
        content_type = content_types.get(extension)
        if not content_type:
            raise ValueError("Only PDF, Markdown, and TXT documents are supported.")

        from app.core.settings import settings
        if not settings.enable_object_storage:
            raise ValueError("Private R2 storage must be enabled before adding knowledge documents.")
        from app.services.storage_service import MAX_DOC_BYTES, upload_to_r2
        url, _ = await upload_to_r2(
            file_bytes=content,
            folder="ragdocs",
            filename=filename,
            content_type=content_type,
            max_size=MAX_DOC_BYTES,
            allowed_types=frozenset({content_type}),
            private=True,
        )
        data["filename"] = filename
        data["file_path"] = url

        from app.core.database import get_session
        from app.services.ai_service import process_and_embed_document

        async def ingest():
            async for session in get_session():
                await process_and_embed_document(
                    content,
                    filename,
                    data.get("language", "pt"),
                    session,
                )

        await ingest()
