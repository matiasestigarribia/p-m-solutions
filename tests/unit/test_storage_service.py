import asyncio
from io import BytesIO

import pytest
from PIL import Image

from app.services import storage_service


def _png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (2, 2), "white").save(output, format="PNG")
    return output.getvalue()


def test_safe_key_removes_path_segments_and_restricts_folder():
    key = storage_service._safe_key("contact", r"../../private\document.pdf")
    assert key.startswith("contact/")
    assert ".." not in key
    assert "\\" not in key
    with pytest.raises(ValueError):
        storage_service._safe_key("arbitrary", "file.txt")


def test_upload_signature_rejects_fake_image():
    with pytest.raises(ValueError, match="declared type"):
        storage_service.validate_upload_content(b"not an image", "image/png")


def test_upload_signature_accepts_real_png():
    storage_service.validate_upload_content(_png_bytes(), "image/png")


def test_upload_signature_rejects_image_with_wrong_declared_type():
    with pytest.raises(ValueError, match="declared type"):
        storage_service.validate_upload_content(_png_bytes(), "image/jpeg")


def test_private_upload_uses_private_bucket(monkeypatch):
    captured = {}

    def fake_upload(file_bytes, key, content_type, bucket_name, private):
        captured.update(
            key=key,
            content_type=content_type,
            bucket_name=bucket_name,
            private=private,
        )
        return "https://signed.example/file"

    monkeypatch.setattr(storage_service, "_upload_sync", fake_upload)
    async def run_upload():
        return await storage_service.upload_to_r2(
            file_bytes=_png_bytes(),
            folder="contact",
            filename="brief.png",
            content_type="image/png",
            private=True,
            bucket_name="private-bucket",
        )

    url, key = asyncio.run(run_upload())

    assert url == "https://signed.example/file"
    assert key == captured["key"]
    assert captured["bucket_name"] == "private-bucket"
    assert captured["private"] is True
