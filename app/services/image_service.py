"""Image optimisation: resize + convert to WebP via Pillow (async-safe)."""
from __future__ import annotations

import asyncio
import os
from io import BytesIO

from PIL import Image


def _optimise_sync(content: bytes, filename: str) -> tuple[bytes, str]:
    image = Image.open(BytesIO(content))
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")
    image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)

    base = os.path.splitext(filename)[0]
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in base.lower())
    new_filename = f"{safe}.webp"

    buf = BytesIO()
    image.save(buf, format="WEBP", quality=80)
    return buf.getvalue(), new_filename


async def optimize_image_bytes(upload_file, content: bytes | None = None) -> tuple[bytes, str]:
    """Optimise an upload file (or pre-read bytes) to WebP.

    Accepts either an UploadFile object or pre-read bytes + filename.
    Returns (webp_bytes, new_filename).
    """
    if content is None:
        content = await upload_file.read()
    filename = getattr(upload_file, "filename", "image.jpg") or "image.jpg"
    return await asyncio.to_thread(_optimise_sync, content, filename)
