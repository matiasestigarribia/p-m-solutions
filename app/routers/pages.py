"""Public content pages.

When enable_database=True, content is read from Neon; a missing row falls
back to site_content.py so the site stays live before seed data is loaded.
When enable_database=False (dev / test without DB), site_content.py is used
directly — no DB connection is attempted.

Templates always receive a ``content`` namespace with the same attribute names
as the site_content module, so no template changes are needed.
"""
from __future__ import annotations

import types

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from starlette.responses import Response

from app.content import site_content
from app.core.security import issue_csrf_token
from app.core.settings import settings
from app.core.templating import base_context, is_htmx, templates

router = APIRouter()

CSRF_COOKIE = "pm_csrf"


def set_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        CSRF_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        max_age=60 * 60 * 4,
    )


async def get_optional_db():
    """FastAPI dependency: AsyncSession or None."""
    if not settings.enable_database:
        yield None
        return
    try:
        from app.core.database import get_session
        async for session in get_session():
            yield session
            return
    except Exception:
        if settings.environment == "production":
            raise
        yield None


# ---------------------------------------------------------------------------
# Content proxy: builds a namespace that mimics the site_content module,
# overriding specific attributes with DB-fetched values when available.
# ---------------------------------------------------------------------------

def _section_from_row(row) -> site_content.Section:
    """Convert a DB content entity to a Section dataclass."""
    return site_content.Section(
        title=row.title,
        paragraphs=tuple(row.paragraphs or []),
    )


async def _build_content(db) -> types.SimpleNamespace:
    """Return a content namespace for template rendering.

    # Queries DB for the four content entities and active products.
    # Production requires the approved CMS rows to exist; only dev/test may
    # use the static source as a fallback.
    """
    ns = types.SimpleNamespace()
    # Copy all public attributes from site_content as defaults
    for attr in dir(site_content):
        if not attr.startswith("_"):
            setattr(ns, attr, getattr(site_content, attr))

    if db is None:
        return ns

    from sqlalchemy import select

    from app.models.company import Company
    from app.models.mission import Mission
    from app.models.products import Product
    from app.models.purpose import Purpose
    from app.models.vision import Vision

    missing: list[str] = []
    try:
        r = await db.execute(select(Company).limit(1))
        row = r.scalar_one_or_none()
        if row:
            ns.QUEM_SOMOS = _section_from_row(row)
        else:
            missing.append("company")

        r = await db.execute(select(Mission).limit(1))
        row = r.scalar_one_or_none()
        if row:
            ns.MISSAO = _section_from_row(row)
        else:
            missing.append("mission")

        r = await db.execute(select(Vision).limit(1))
        row = r.scalar_one_or_none()
        if row:
            ns.VISAO = _section_from_row(row)
        else:
            missing.append("vision")

        r = await db.execute(select(Purpose).limit(1))
        row = r.scalar_one_or_none()
        if row:
            ns.PROPOSITO = _section_from_row(row)
        else:
            missing.append("purpose")

        ns.COMPANY_SECTIONS = (ns.QUEM_SOMOS, ns.MISSAO, ns.VISAO, ns.PROPOSITO)
        ns.MVP_SECTIONS = (ns.MISSAO, ns.VISAO, ns.PROPOSITO)

        r = await db.execute(
            select(Product)
            .where(Product.is_active.is_(True))
            .order_by(Product.display_order)
        )
        db_products = r.scalars().all()
        if db_products:
            ns.PRODUCTS = tuple(db_products)

        if missing and settings.environment == "production":
            raise RuntimeError("Required CMS content is missing.")

    except Exception:
        if settings.environment == "production":
            raise
        # DB unavailable at runtime — use site_content fallback

    return ns


# ---------------------------------------------------------------------------
# Route helpers
# ---------------------------------------------------------------------------

def _render_page(request: Request, fragment: str, content_ns=None, *, csrf: bool = False):
    extra: dict = {"active_fragment": fragment}
    if content_ns is not None:
        extra["content"] = content_ns
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db=Depends(get_optional_db)):
    content_ns = await _build_content(db)
    return _render_page(request, "fragments/home.html", content_ns)


@router.get("/quem-somos", response_class=HTMLResponse)
async def company(request: Request, db=Depends(get_optional_db)):
    content_ns = await _build_content(db)
    return _render_page(request, "fragments/company.html", content_ns)


@router.get("/produtos", response_class=HTMLResponse)
async def products(request: Request, db=Depends(get_optional_db)):
    content_ns = await _build_content(db)
    return _render_page(request, "fragments/products.html", content_ns)


@router.get("/contato", response_class=HTMLResponse)
async def contact(request: Request, db=Depends(get_optional_db)):
    content_ns = await _build_content(db)
    return _render_page(request, "fragments/contact.html", content_ns, csrf=True)


@router.get("/chat", response_class=HTMLResponse)
async def chat_modal(request: Request, lang: str = "pt"):
    """Return the Portuguese chat modal fragment for HTMX."""
    context = base_context(request, chat_language="pt", requested_chat_language=lang)
    return templates.TemplateResponse(request, "fragments/chat_modal.html", context)
