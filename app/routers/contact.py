"""Contact form submission handler.

When enable_database=True: persists ContactMessage to Neon via async SQLAlchemy.
When enable_database=False: uses the local contact sink (SQLite or logging).
Production with enable_database=True will NOT silently fall back to SQLite —
if the DB is unreachable the request fails with an error response.

Security: signed-token + double-submit CSRF, honeypot, per-IP rate limit.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.core.security import RateLimiter, issue_csrf_token, validate_csrf_token
from app.core.templating import base_context, is_htmx, templates
from app.routers.pages import CSRF_COOKIE, get_optional_db, set_csrf_cookie
from app.core.settings import settings
from app.schemas.contact import ContactSubmission
from app.services.contact_sink import get_contact_sink

router = APIRouter()

_limiter = RateLimiter(limit=settings.contact_rate_limit_per_hour, window_seconds=3600)

_FORM_FIELDS = (
    "full_name", "company", "email", "phone", "location", "solution",
    "project_stage", "need", "priority", "deadline", "contact_preference",
    "best_time",
)

_REQUIRED_MSG = "Campo obrigatório."


def _client_ip(request: Request) -> str:
    # Do not trust client-controlled forwarding headers. Cloud Run supplies the
    # direct peer address to the application process.
    return request.client.host if request.client else "unknown"


def _errors_from_validation(exc: ValidationError) -> dict:
    errors: dict[str, str] = {}
    for err in exc.errors():
        loc = err["loc"][0] if err["loc"] else "__form__"
        if err["type"] in ("missing", "string_too_short") and loc != "consent":
            errors[str(loc)] = _REQUIRED_MSG
        else:
            errors[str(loc)] = err.get("msg", "Valor inválido.")
    return errors


async def _persist(
    submission: ContactSubmission,
    db,
    attachment_url: str | None = None,
    attachment_key: str | None = None,
) -> None:
    """Save submission to DB (when enabled) or local sink (dev fallback)."""
    if db is not None and settings.enable_database:
        from app.models.contact_messages import ContactMessage as ContactMessageModel

        msg = ContactMessageModel(
            full_name=submission.full_name,
            company=submission.company or "",
            email=str(submission.email),
            phone=submission.phone,
            location=submission.location or "",
            solution=submission.solution,
            project_stage=submission.project_stage,
            need=submission.need,
            priority=submission.priority,
            deadline=submission.deadline or "",
            attachment_url=attachment_url,
            attachment_key=attachment_key,
            contact_preference=submission.contact_preference,
            best_time=submission.best_time,
        )
        db.add(msg)
        await db.commit()
    elif settings.enable_database:
        # DB is enabled but session unavailable — fail loudly in production
        if settings.environment == "production":
            raise RuntimeError("Database unavailable; cannot persist contact message.")
        get_contact_sink(settings).save(submission)
    else:
        get_contact_sink(settings).save(submission)


@router.post("/contato", response_class=HTMLResponse)
async def submit_contact(request: Request, db=Depends(get_optional_db)):
    form = await request.form()

    # 1) Rate limit
    if not _limiter.allow(_client_ip(request)):
        return _render_form(
            request, values={},
            errors={"__form__": "Muitas solicitações. Tente novamente mais tarde."},
            status_code=429,
        )

    # 2) CSRF double-submit
    form_token = form.get("csrf_token")
    cookie_token = request.cookies.get(CSRF_COOKIE)
    if not validate_csrf_token(settings.secret_key, form_token) or form_token != cookie_token:
        return _render_form(
            request, values={},
            errors={"__form__": "Sessão expirada. Recarregue a página e tente novamente."},
            status_code=400,
        )

    # 3) Honeypot
    if (form.get("website") or "").strip():
        return _render_success(request)

    # 4) Validate
    raw = {k: (form.get(k) or "") for k in _FORM_FIELDS}
    raw["consent"] = bool(form.get("consent"))
    values = dict(raw)
    try:
        submission = ContactSubmission(**raw)
    except ValidationError as exc:
        return _render_form(request, values=values, errors=_errors_from_validation(exc), status_code=422)

    # 5) Attachment
    attachment_value = form.get("attachment")
    attachment_file = (
        attachment_value
        if isinstance(attachment_value, UploadFile) and attachment_value.filename
        else None
    )

    attachment_url: str | None = None
    attachment_key: str | None = None

    if attachment_file is not None:
        if settings.environment == "production" and not settings.enable_object_storage:
            return _render_form(
                request, values=values,
                errors={"__form__": "Envio de anexos não está disponível no momento."},
                status_code=422,
            )
        if settings.enable_object_storage:
            from app.services.storage_service import (
                ALLOWED_DOCUMENT_TYPES,
                ALLOWED_IMAGE_TYPES,
                MAX_DOC_BYTES,
                MAX_IMAGE_BYTES,
                upload_to_r2,
            )
            ct = getattr(attachment_file, "content_type", None) or ""
            if ct not in (ALLOWED_DOCUMENT_TYPES | ALLOWED_IMAGE_TYPES):
                return _render_form(
                    request, values=values,
                    errors={"attachment": "Tipo de arquivo não permitido."},
                    status_code=422,
                )
            try:
                declared_max_size = MAX_IMAGE_BYTES if ct.startswith("image/") else MAX_DOC_BYTES
                file_bytes = await attachment_file.read(MAX_DOC_BYTES + 1)
            except Exception:
                return _render_form(
                    request, values=values,
                    errors={"attachment": "Erro ao ler arquivo. Tente novamente."},
                    status_code=500,
                )
            if len(file_bytes) > declared_max_size:
                return _render_form(
                    request, values=values,
                    errors={"attachment": f"Arquivo muito grande (máx {declared_max_size // 1024 // 1024} MB)."},
                    status_code=422,
                )
            try:
                attachment_url, attachment_key = await upload_to_r2(
                    file_bytes=file_bytes,
                    folder="contact",
                    filename=attachment_file.filename or "upload",
                    content_type=ct,
                    max_size=declared_max_size,
                    private=True,
                    bucket_name=settings.r2_private_bucket_name,
                )
            except Exception:
                return _render_form(
                    request, values=values,
                    errors={"attachment": "Erro ao enviar arquivo. Tente novamente."},
                    status_code=500,
                )
        # else: R2 disabled in dev/test — ignore attachment

    # 6) Persist
    try:
        await _persist(submission, db, attachment_url=attachment_url, attachment_key=attachment_key)
    except Exception:
        return _render_form(
            request, values=values,
            errors={"__form__": "Erro ao salvar. Tente novamente."},
            status_code=500,
        )

    return _render_success(request)


def _render_form(request: Request, values: dict, errors: dict, status_code: int) -> HTMLResponse:
    token = issue_csrf_token(settings.secret_key)
    ctx = base_context(request, csrf_token=token, values=values, errors=errors)
    ctx["active_fragment"] = "fragments/contact.html"
    template = "partials/contact_form.html" if is_htmx(request) else "index.html"
    html = templates.get_template(template).render(ctx)
    response = HTMLResponse(html, status_code=status_code)
    set_csrf_cookie(response, token)
    return response


def _render_success(request: Request) -> HTMLResponse:
    ctx = base_context(request, submitted=True)
    ctx["active_fragment"] = "fragments/contact.html"
    template = "partials/contact_success.html" if is_htmx(request) else "index.html"
    html = templates.get_template(template).render(ctx)
    return HTMLResponse(html)
