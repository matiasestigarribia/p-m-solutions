"""Public content pages."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from starlette.responses import Response

from app.core.security import issue_csrf_token
from app.core.settings import settings
from app.core.templating import base_context, is_htmx, templates

router = APIRouter()

CSRF_COOKIE = "pm_csrf"


def set_csrf_cookie(response: Response, token: str) -> None:
    """Pin the CSRF token in an http-only cookie (double-submit protection)."""
    response.set_cookie(
        CSRF_COOKIE, token,
        httponly=True, samesite="lax",
        secure=settings.environment == "production",
        max_age=60 * 60 * 4,
    )


def _render_page(request: Request, fragment: str, *, csrf: bool = False):
    """Render the full shell or only the requested HTMX page fragment."""
    extra = {"active_fragment": fragment}
    token = None
    if csrf:
        token = issue_csrf_token(settings.secret_key)
        extra["csrf_token"] = token

    context = base_context(request, **extra)
    template = fragment if is_htmx(request) else "index.html"
    page = templates.TemplateResponse(request, template, context)
    if csrf:
        assert token is not None
        set_csrf_cookie(page, token)
    return page


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return _render_page(request, "fragments/home.html")


@router.get("/quem-somos", response_class=HTMLResponse)
async def company(request: Request):
    return _render_page(request, "fragments/company.html")


@router.get("/produtos", response_class=HTMLResponse)
async def products(request: Request):
    return _render_page(request, "fragments/products.html")


@router.get("/contato", response_class=HTMLResponse)
async def contact(request: Request):
    return _render_page(request, "fragments/contact.html", csrf=True)
