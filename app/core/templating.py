"""Shared Jinja2 templates instance and page-context helper."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.content import site_content
from app.core.settings import settings

templates = Jinja2Templates(directory="templates")


def base_context(request: Request, **extra) -> dict:
    """Context every page/partial needs."""
    ctx = {
        "request": request,
        "project_name": settings.project_name,
        "year": datetime.now(timezone.utc).year,
        "content": site_content,
        "contact_info_fields": site_content.CONTACT_INFO_FIELDS,
        "project_fields": site_content.PROJECT_FIELDS,
        "values": {},
        "errors": {},
        "submitted": False,
        "active_fragment": "fragments/home.html",
    }
    ctx.update(extra)
    return ctx


def is_htmx(request: Request) -> bool:
    return request.headers.get("hx-request") == "true"
