"""P & M Solutions — MVP application.

DB stack (SQLAdmin + engine) is mounted only when PM_ENABLE_DATABASE=true,
so the app boots cleanly in dev/test with no DB credentials present.
The health endpoint pings the database when enabled.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.settings import settings
from app.routers import chat, contact, pages

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description="Public content site and contact form for P & M Solutions (MVP).",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages.router, tags=["Pages"])
app.include_router(contact.router, tags=["Contact"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chatbot"])

# ---------------------------------------------------------------------------
# Admin panel — mounted only when DB is enabled
# ---------------------------------------------------------------------------
if settings.enable_database:
    from app.admin.admin import UrlAwareAdmin
    from app.admin.auth import get_authentication_backend
    from app.admin.views import (
        ChatLogAdmin,
        CompanyAdmin,
        ContactMessageAdmin,
        MissionAdmin,
        ProductAdmin,
        PurposeAdmin,
        RagDocumentAdmin,
        UploadedDocumentAdmin,
        UserAdmin,
        VisionAdmin,
    )
    from app.core.database import get_engine

    _admin = UrlAwareAdmin(
        app=app,
        engine=get_engine(),
        authentication_backend=get_authentication_backend(),
        title="P & M Solutions Admin",
    )
    _admin.add_view(UserAdmin)
    _admin.add_view(CompanyAdmin)
    _admin.add_view(MissionAdmin)
    _admin.add_view(VisionAdmin)
    _admin.add_view(PurposeAdmin)
    _admin.add_view(ProductAdmin)
    _admin.add_view(ContactMessageAdmin)
    _admin.add_view(RagDocumentAdmin)
    _admin.add_view(ChatLogAdmin)
    _admin.add_view(UploadedDocumentAdmin)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Ops"])
async def health_check():
    """Liveness/readiness probe for Cloud Run.

    Pings the database when enabled so Cloud Run readiness reflects DB state.
    """
    result: dict = {
        "status": "ok",
        "version": settings.version,
        "environment": settings.environment,
        "integrations": {
            "database": settings.enable_database,
            "object_storage": settings.enable_object_storage,
            "chatbot": settings.enable_chatbot,
        },
    }

    if settings.enable_database:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.core.database import get_engine

        try:
            async with AsyncSession(get_engine()) as db:
                await db.execute(text("SELECT 1"))
            result["database_status"] = "connected"
        except Exception:
            logger.exception("Database health check failed")
            result["database_status"] = "error"
            result["status"] = "degraded"
            from fastapi.responses import JSONResponse
            return JSONResponse(content=result, status_code=503)

    return result
