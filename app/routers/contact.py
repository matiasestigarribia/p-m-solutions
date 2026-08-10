"""Contact form submission handler (Stage 1).

Server-side validation, signed-token + double-submit CSRF protection, a honeypot
field, and an in-memory per-IP rate limit — none of which require an external
service. Submissions are persisted through the ContactSink seam (logging or
local SQLite), never a remote database.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.core.security import RateLimiter, issue_csrf_token, validate_csrf_token
from app.core.templating import base_context, is_htmx, templates
from app.routers.pages import CSRF_COOKIE, set_csrf_cookie
from app.core.settings import settings
from app.schemas.contact import ContactSubmission
from app.services.contact_sink import get_contact_sink

router = APIRouter()

_limiter = RateLimiter(limit=settings.contact_rate_limit_per_hour, window_seconds=3600)

# Submission field names read from the form (attachment excluded — Stage 2 R2).
_FORM_FIELDS = (
    "full_name", "company", "email", "phone", "location", "solution",
    "project_stage", "need", "priority", "deadline", "contact_preference",
    "best_time",
)

_REQUIRED_MSG = "Campo obrigatório."


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
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


@router.post("/contato", response_class=HTMLResponse)
async def submit_contact(request: Request):
    form = await request.form()

    # 1) Rate limit (local, per-IP).
    if not _limiter.allow(_client_ip(request)):
        return _render_form(
            request, values={}, errors={"__form__": "Muitas solicitações. Tente novamente mais tarde."},
            status_code=429,
        )

    # 2) CSRF: form token must be validly signed AND match the cookie.
    form_token = form.get("csrf_token")
    cookie_token = request.cookies.get(CSRF_COOKIE)
    if not validate_csrf_token(settings.secret_key, form_token) or form_token != cookie_token:
        return _render_form(
            request, values={}, errors={"__form__": "Sessão expirada. Recarregue a página e tente novamente."},
            status_code=400,
        )

    # 3) Honeypot: real users never fill this.
    if (form.get("website") or "").strip():
        # Silently accept to avoid signalling the bot; do not persist.
        return _render_success(request)

    # 4) Assemble + validate.
    raw = {k: (form.get(k) or "") for k in _FORM_FIELDS}
    raw["consent"] = bool(form.get("consent"))
    values = dict(raw)
    try:
        submission = ContactSubmission(**raw)
    except ValidationError as exc:
        return _render_form(request, values=values, errors=_errors_from_validation(exc), status_code=422)

    # 5) Persist through the sink seam.
    get_contact_sink(settings).save(submission)
    return _render_success(request)


def _render_form(request: Request, values: dict, errors: dict, status_code: int) -> HTMLResponse:
    # Issue a fresh CSRF token, embed it in the re-rendered form, and pin the
    # matching cookie so the retry validates.
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
