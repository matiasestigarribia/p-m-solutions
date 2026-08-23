"""UrlAwareAdmin — fixes sqladmin file-field crash when DB stores a URL string.

When a FileField column holds a URL string and the edit form submits an empty
file upload, stock sqladmin tries to call `.name` / `.open()` on the string
(AttributeError). This override detects that case and passes the string through
unchanged so `on_model_change` can decide to skip the upload.
"""
from __future__ import annotations

import io
from typing import Any

from sqladmin import Admin
from starlette.datastructures import FormData, UploadFile
from starlette.requests import Request


class UrlAwareAdmin(Admin):
    async def _handle_form_data(self, request: Request, obj: Any = None) -> FormData:
        form = await request.form()
        form_data: list[tuple[str, str | UploadFile]] = []

        for key, value in form.multi_items():
            if not isinstance(value, UploadFile):
                form_data.append((key, value))
                continue

            should_clear = form.get(key + "_checkbox")
            empty_upload = len(await value.read(1)) != 1
            await value.seek(0)

            if should_clear:
                form_data.append((key, UploadFile(io.BytesIO(b""))))
            elif empty_upload and obj and getattr(obj, key):
                existing = getattr(obj, key)
                if isinstance(existing, str):
                    form_data.append((key, existing))
                else:
                    form_data.append(
                        (key, UploadFile(filename=existing.name, file=existing.open()))
                    )
            else:
                form_data.append((key, value))

        return FormData(form_data)
