"""Cloudflare R2 storage adapter (async-safe via asyncio.to_thread).

The boto3 client is created lazily per call — never at import time — so the
module can be imported safely in tests without R2 credentials. Mock
`app.services.storage_service._upload_sync` or patch `boto3.client` in tests.

Content-type and size validation happen before the upload. Object keys are
sanitised: UUID prefix + ASCII-safe filename, no spaces or path traversal.
"""
from __future__ import annotations

import asyncio
from io import BytesIO
import os
import uuid
import zipfile

from PIL import Image, UnidentifiedImageError

from app.core.settings import settings

# Permitted content types and their max sizes
ALLOWED_IMAGE_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/gif", "image/webp"}
)
ALLOWED_DOCUMENT_TYPES = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/zip",
    }
)
MAX_IMAGE_BYTES = 10 * 1024 * 1024   # 10 MB
MAX_DOC_BYTES = 20 * 1024 * 1024     # 20 MB


def _safe_key(folder: str, filename: str) -> str:
    """Generate a collision-resistant, path-safe object key."""
    if folder not in {"products", "contact", "ragdocs"}:
        raise ValueError("Unsupported storage folder.")
    filename = os.path.basename(filename.replace("\\", "/"))
    name, ext = os.path.splitext(filename)
    safe_name = "".join(
        c if c.isalnum() or c in "-_" else "_" for c in name.lower()
    )
    safe_name = safe_name or "upload"
    safe_ext = "".join(c for c in ext.lower() if c.isalnum() or c == ".")
    if safe_ext and not safe_ext.startswith("."):
        safe_ext = "." + safe_ext
    uid = uuid.uuid4().hex[:12]
    return f"{folder}/{uid}_{safe_name}{safe_ext}"


def validate_upload_content(file_bytes: bytes, content_type: str) -> None:
    """Validate the payload signature, not only the browser MIME header."""
    if content_type in ALLOWED_IMAGE_TYPES:
        try:
            with Image.open(BytesIO(file_bytes)) as image:
                actual_type = {
                    "JPEG": "image/jpeg",
                    "PNG": "image/png",
                    "GIF": "image/gif",
                    "WEBP": "image/webp",
                }.get(image.format)
                image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError("Image content does not match its declared type.") from exc
        if actual_type != content_type:
            raise ValueError("Image content does not match its declared type.")
        return
    if content_type == "application/pdf" and not file_bytes.startswith(b"%PDF-"):
        raise ValueError("PDF content does not match its declared type.")
    if content_type in {
        "application/zip",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }:
        archive = BytesIO(file_bytes)
        if not zipfile.is_zipfile(archive):
            raise ValueError("Archive content does not match its declared type.")
        with zipfile.ZipFile(archive) as package:
            names = set(package.namelist())
        if content_type.endswith("wordprocessingml.document") and not any(
            name.startswith("word/") for name in names
        ):
            raise ValueError("DOCX content does not match its declared type.")
        if content_type.endswith("spreadsheetml.sheet") and not any(
            name.startswith("xl/") for name in names
        ):
            raise ValueError("XLSX content does not match its declared type.")
    if content_type in {"text/plain", "text/markdown", "text/csv"}:
        try:
            file_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Text content is not valid UTF-8.") from exc


def _upload_sync(
    file_bytes: bytes,
    key: str,
    content_type: str,
    bucket_name: str,
    private: bool,
) -> str:
    """Blocking S3 put_object — run via asyncio.to_thread."""
    import boto3
    from botocore.config import Config

    client = boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key,
        aws_secret_access_key=settings.r2_secret_key,
        config=Config(signature_version="s3v4"),
    )
    client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    if private:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": key},
            ExpiresIn=7 * 24 * 60 * 60,
        )
    if not settings.r2_public_url:
        raise RuntimeError("PM_R2_PUBLIC_URL is required for public media uploads.")
    return f"{settings.r2_public_url.rstrip('/')}/{key}"


async def upload_to_r2(
    file_bytes: bytes,
    folder: str,
    filename: str,
    content_type: str,
    max_size: int = MAX_IMAGE_BYTES,
    allowed_types: frozenset[str] | None = None,
    private: bool = False,
    bucket_name: str | None = None,
) -> tuple[str, str]:
    """Upload bytes to R2. Returns (public_url, object_key).

    Raises ValueError for unsupported content type or size violations.
    """
    _allowed = allowed_types or (ALLOWED_IMAGE_TYPES | ALLOWED_DOCUMENT_TYPES)
    if content_type not in _allowed:
        raise ValueError(f"Unsupported content type: {content_type!r}.")
    if len(file_bytes) > max_size:
        raise ValueError(
            f"File too large: {len(file_bytes) // 1024} KB "
            f"(max {max_size // 1024 // 1024} MB)."
        )
    validate_upload_content(file_bytes, content_type)
    target_bucket = bucket_name or (
        settings.r2_private_bucket_name if private else settings.r2_bucket_name
    )
    if not target_bucket:
        raise ValueError("No R2 bucket configured for this upload.")
    key = _safe_key(folder, filename)
    url = await asyncio.to_thread(
        _upload_sync, file_bytes, key, content_type, target_bucket, private
    )
    return url, key
