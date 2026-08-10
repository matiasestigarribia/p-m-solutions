"""P & M Solutions — Stage 1 application (content site + contact form).

Stage 1 boots with an empty environment: no Neon, no Cloudflare R2, no chatbot,
no LLM, no vector search. Those are guarded behind ``app.services.integrations``
seams and stay inactive. Nothing heavy is imported at module load.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.settings import settings
from app.routers import contact, pages

app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description="Public content site and contact form for P & M Solutions (Stage 1).",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages.router, tags=["Pages"])
app.include_router(contact.router, tags=["Contact"])


@app.get("/health", tags=["Ops"])
async def health_check():
    """Liveness/readiness probe for Cloud Run.

    Stage 1 has no database to ping — the endpoint reports which deferred
    integrations are active so ops can see the running configuration.
    """
    return {
        "status": "ok",
        "stage": 1,
        "version": settings.version,
        "integrations": {
            "database": settings.enable_database,
            "object_storage": settings.enable_object_storage,
            "chatbot": settings.enable_chatbot,
        },
    }
