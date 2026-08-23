# MVP Repair: Contact Attachments, DB Strictness, R2 Validation, Admin Safety

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix six concrete blockers in the P&M Solutions MVP: contact attachment wiring, production DB strictness, production integration settings validation, R2 type validation, admin password hashing, and focused tests for all.

**Architecture:** Each blocker maps to ≤2 files. Changes are additive (no structural refactor). Tests are added alongside each fix.

**Tech Stack:** FastAPI, SQLAlchemy async, Jinja2, sqladmin, boto3/R2, pytest, pydantic-settings.

**Spec:** User prompt — 6 enumerated blockers.

## Global Constraints

- Never log secrets (env vars, keys, passwords)
- Development/test defaults must keep working (no PM_* env required)
- Preserve existing 58-test passing behavior; only update tests whose asserted behavior changes
- Do not commit, push, or merge
- `uv run` is not available; use `.venv/bin/pytest`

---

### Task 1: R2 content-type validation in storage_service.py

**Files:**
- Modify: `app/services/storage_service.py`
- Test: `tests/unit/test_storage_service.py` (new)

**Interfaces:**
- `upload_to_r2(file_bytes, folder, filename, content_type, allowed_types=None, max_size=MAX_IMAGE_BYTES) -> tuple[str, str]`
- Raises `ValueError` for bad content-type or oversized file

- [ ] **Step 1: Create test file with failing tests**

```python
# tests/unit/test_storage_service.py
import pytest
from unittest.mock import AsyncMock, patch

from app.services.storage_service import (
    ALLOWED_DOCUMENT_TYPES,
    ALLOWED_IMAGE_TYPES,
    MAX_DOC_BYTES,
    MAX_IMAGE_BYTES,
    upload_to_r2,
)


@pytest.mark.anyio
async def test_upload_rejects_disallowed_content_type():
    with pytest.raises(ValueError, match="Unsupported content type"):
        await upload_to_r2(
            file_bytes=b"data",
            folder="test",
            filename="file.exe",
            content_type="application/x-msdownload",
            allowed_types=ALLOWED_DOCUMENT_TYPES,
        )


@pytest.mark.anyio
async def test_upload_rejects_oversized_file():
    big = b"x" * (MAX_IMAGE_BYTES + 1)
    with pytest.raises(ValueError, match="too large"):
        await upload_to_r2(
            file_bytes=big,
            folder="test",
            filename="file.jpg",
            content_type="image/jpeg",
            allowed_types=ALLOWED_IMAGE_TYPES,
        )


@pytest.mark.anyio
async def test_upload_skips_type_check_when_allowed_types_is_none():
    with patch("app.services.storage_service._upload_sync", return_value="https://r2.example/test/abc_file.jpg"):
        url, key = await upload_to_r2(
            file_bytes=b"data",
            folder="test",
            filename="file.jpg",
            content_type="image/jpeg",
            allowed_types=None,
        )
    assert url.startswith("https://")
    assert "test/" in key


@pytest.mark.anyio
async def test_upload_accepts_valid_type_and_size():
    with patch("app.services.storage_service._upload_sync", return_value="https://r2.example/test/abc_file.pdf"):
        url, key = await upload_to_r2(
            file_bytes=b"pdf content",
            folder="test",
            filename="brief.pdf",
            content_type="application/pdf",
            allowed_types=ALLOWED_DOCUMENT_TYPES,
        )
    assert url
    assert key.startswith("test/")
```

- [ ] **Step 2: Add anyio to pyproject.toml dev deps and run test to verify FAIL**

Add `"anyio[trio]>=4.4"` to `dev` deps if not already there. Then:
```
.venv/bin/pytest tests/unit/test_storage_service.py -v
```
Expected: FAIL (TypeError because upload_to_r2 doesn't accept allowed_types)

- [ ] **Step 3: Implement allowed_types parameter in upload_to_r2**

In `app/services/storage_service.py`, change the signature and add validation:

```python
async def upload_to_r2(
    file_bytes: bytes,
    folder: str,
    filename: str,
    content_type: str,
    allowed_types: frozenset | None = None,
    max_size: int = MAX_IMAGE_BYTES,
) -> tuple[str, str]:
    if allowed_types is not None and content_type not in allowed_types:
        raise ValueError(f"Unsupported content type: {content_type!r}.")
    if len(file_bytes) > max_size:
        raise ValueError(
            f"File too large: {len(file_bytes) // 1024} KB "
            f"(max {max_size // 1024 // 1024} MB)."
        )
    key = _safe_key(folder, filename)
    public_url = await asyncio.to_thread(_upload_sync, file_bytes, key, content_type)
    return public_url, key
```

Remove the duplicate size check that was already in the old version.

- [ ] **Step 4: Run tests — expect PASS**

```
.venv/bin/pytest tests/unit/test_storage_service.py -v
```

- [ ] **Step 5: Run full suite to ensure no regressions**

```
.venv/bin/pytest -q
```

---

### Task 2: Production integration settings (DB + storage required in prod)

**Files:**
- Modify: `app/core/settings.py`
- Modify: `tests/unit/test_settings_production_secret.py` (update one test)
- Test: `tests/unit/test_settings.py` (add two tests at bottom)

**Interfaces:**
- `Settings._validate()` raises `ValueError` when `environment="production"` and `enable_database=False` or `enable_object_storage=False`

- [ ] **Step 1: Add failing tests to test_settings.py**

Append to `tests/unit/test_settings.py`:

```python
def test_production_requires_enable_database(monkeypatch):
    for var in ("PM_ENVIRONMENT", "PM_SECRET_KEY", "PM_ENABLE_DATABASE",
                "PM_ENABLE_OBJECT_STORAGE", "PM_DATABASE_URL",
                "PM_R2_ENDPOINT_URL", "PM_R2_ACCESS_KEY", "PM_R2_SECRET_KEY",
                "PM_R2_BUCKET_NAME", "PM_R2_PUBLIC_URL"):
        monkeypatch.delenv(var, raising=False)
    from app.core.settings import Settings
    with pytest.raises(ValueError, match="PM_ENABLE_DATABASE"):
        Settings(
            _env_file=None,
            environment="production",
            secret_key="strong-prod-secret",
            enable_database=False,
            enable_object_storage=True,
            r2_endpoint_url="https://r2.example",
            r2_access_key="key",
            r2_secret_key="secret",
            r2_bucket_name="bucket",
            r2_public_url="https://pub.example",
        )


def test_production_requires_enable_object_storage(monkeypatch):
    for var in ("PM_ENVIRONMENT", "PM_SECRET_KEY", "PM_ENABLE_DATABASE",
                "PM_ENABLE_OBJECT_STORAGE", "PM_DATABASE_URL"):
        monkeypatch.delenv(var, raising=False)
    from app.core.settings import Settings
    with pytest.raises(ValueError, match="PM_ENABLE_OBJECT_STORAGE"):
        Settings(
            _env_file=None,
            environment="production",
            secret_key="strong-prod-secret",
            enable_database=True,
            database_url="postgresql+asyncpg://user:pass@host/db",
            enable_object_storage=False,
        )
```

- [ ] **Step 2: Run new tests — expect FAIL**

```
.venv/bin/pytest tests/unit/test_settings.py -v -k "production_requires"
```

- [ ] **Step 3: Add production validation to Settings._validate()**

In `app/core/settings.py`, inside `_validate`, add after the existing secret_key check:

```python
        if self.environment == "production":
            if not self.enable_database:
                raise ValueError(
                    "PM_ENABLE_DATABASE=true is required when PM_ENVIRONMENT=production."
                )
            if not self.enable_object_storage:
                raise ValueError(
                    "PM_ENABLE_OBJECT_STORAGE=true is required when PM_ENVIRONMENT=production."
                )
```

- [ ] **Step 4: Update test_production_accepts_real_secret to supply full prod config**

In `tests/unit/test_settings_production_secret.py`, `test_production_accepts_real_secret` must now supply DB + R2 settings to pass validation:

```python
def test_production_accepts_real_secret(monkeypatch):
    _clear_pm_env(monkeypatch)
    from app.core.settings import Settings

    settings = Settings(
        _env_file=None,
        environment="production",
        secret_key="a-real-strong-production-secret",
        enable_database=True,
        database_url="postgresql+asyncpg://user:pass@host/db",
        enable_object_storage=True,
        r2_endpoint_url="https://r2.example.com",
        r2_access_key="AKID",
        r2_secret_key="SECRET",
        r2_bucket_name="pm-bucket",
        r2_public_url="https://pub.r2.example.com",
    )
    assert settings.environment == "production"
    assert settings.secret_key == "a-real-strong-production-secret"
```

- [ ] **Step 5: Run full suite — expect all pass**

```
.venv/bin/pytest -q
```

---

### Task 3: Production DB strictness — /health, get_optional_db, _build_content

**Files:**
- Modify: `app/main.py`
- Modify: `app/routers/pages.py`
- Test: `tests/unit/test_production_db_strictness.py` (new)

**Interfaces:**
- `GET /health` returns HTTP 503 (not 200) when DB is enabled but unavailable
- `get_optional_db` raises `HTTPException(503)` in production when DB session fails
- `_build_content` raises `HTTPException(503)` in production when DB queries fail

- [ ] **Step 1: Create test file with failing tests**

```python
# tests/unit/test_production_db_strictness.py
"""Production DB strictness: fail hard, not silently."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def _prod_settings_overrides(monkeypatch):
    from app.core.settings import settings
    monkeypatch.setattr(settings, "environment", "production", raising=False)
    monkeypatch.setattr(settings, "enable_database", True, raising=False)


def test_health_returns_503_when_db_unavailable(monkeypatch):
    from app.core.settings import settings
    monkeypatch.setattr(settings, "enable_database", True, raising=False)

    with patch("app.core.database.get_engine") as mock_engine:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(side_effect=Exception("DB down"))
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_engine.return_value = MagicMock()

        with patch("sqlalchemy.ext.asyncio.AsyncSession", return_value=mock_session):
            from app.main import app
            client = TestClient(app, raise_server_exceptions=False)
            r = client.get("/health")

    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    assert body["database_status"] == "error"


def test_build_content_raises_503_in_production_on_db_error(monkeypatch):
    from app.core.settings import settings
    monkeypatch.setattr(settings, "environment", "production", raising=False)
    monkeypatch.setattr(settings, "enable_database", True, raising=False)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=Exception("DB query failed"))

    from fastapi import HTTPException
    import asyncio
    from app.routers.pages import _build_content

    with pytest.raises(HTTPException) as exc_info:
        asyncio.get_event_loop().run_until_complete(_build_content(mock_db))
    assert exc_info.value.status_code == 503
```

- [ ] **Step 2: Run test to verify FAIL**

```
.venv/bin/pytest tests/unit/test_production_db_strictness.py -v
```

- [ ] **Step 3: Fix /health to return 503 when degraded**

In `app/main.py`, change the health check to return 503 on degraded:

```python
    if settings.enable_database:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.core.database import get_engine

        try:
            async with AsyncSession(get_engine()) as db:
                await db.execute(text("SELECT 1"))
            result["database_status"] = "connected"
        except Exception as exc:
            result["database_status"] = "error"
            result["database_detail"] = str(exc)
            result["status"] = "degraded"

    if result["status"] == "degraded":
        from fastapi.responses import JSONResponse
        return JSONResponse(content=result, status_code=503)
    return result
```

- [ ] **Step 4: Fix _build_content to raise 503 in production**

In `app/routers/pages.py`, change the except block in `_build_content`:

```python
    except Exception:
        if settings.environment == "production":
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail="Database error loading page content.",
            )
        # DB unavailable at runtime — use site_content fallback (dev/staging only)
```

- [ ] **Step 5: Fix get_optional_db to raise 503 in production**

In `app/routers/pages.py`, change the except block in `get_optional_db`:

```python
async def get_optional_db():
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
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail="Database session unavailable.",
            )
        yield None
```

- [ ] **Step 6: Run tests**

```
.venv/bin/pytest tests/unit/test_production_db_strictness.py -v
.venv/bin/pytest -q
```

---

### Task 4: Contact attachment wiring (template + handler + R2 + DB persist)

**Files:**
- Modify: `templates/partials/_field.html` — enable file input when storage enabled
- Modify: `templates/partials/contact_form.html` — add multipart enctype
- Modify: `app/routers/contact.py` — read UploadFile, validate, upload, persist
- Modify: `app/content/site_content.py` — mark attachment field enabled=True
- Test: `tests/unit/test_contact_attachment.py` (new)
- Test: `tests/integration/test_site.py` (extend)

**Constants needed in contact.py:**
```python
CONTACT_ALLOWED_TYPES = frozenset({
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "image/png",
    "image/jpeg",
    "application/zip",
})
CONTACT_MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024  # 20 MB
```

- [ ] **Step 1: Create test_contact_attachment.py with failing tests**

```python
# tests/unit/test_contact_attachment.py
"""Contact form attachment upload: validation and R2 wiring."""
import io
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import re

from app.core.settings import settings
from app.main import app


@pytest.fixture(autouse=True)
def _local_sink(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "contact_sink", "sqlite", raising=False)
    monkeypatch.setattr(settings, "contact_db_path", str(tmp_path / "c.sqlite3"), raising=False)
    monkeypatch.setattr(settings, "enable_object_storage", False, raising=False)


@pytest.fixture
def client():
    return TestClient(app)


def _get_token(client):
    r = client.get("/contato")
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    return m.group(1)


def _valid_fields(token):
    return {
        "csrf_token": token,
        "full_name": "Ana Lima",
        "company": "",
        "email": "ana@example.com",
        "phone": "(11) 98888-0001",
        "location": "",
        "solution": "Automação de processos",
        "project_stage": "",
        "need": "Automatizar o processo de emissão de notas fiscais mensais.",
        "priority": "",
        "deadline": "",
        "contact_preference": "",
        "best_time": "",
        "consent": "on",
    }


def test_contact_form_has_file_input(client):
    r = client.get("/contato")
    assert 'type="file"' in r.text
    assert 'name="attachment"' in r.text


def test_contact_form_has_multipart_enctype(client):
    r = client.get("/contato")
    assert 'enctype="multipart/form-data"' in r.text


def test_attachment_not_required_submission_succeeds(client):
    token = _get_token(client)
    r = client.post("/contato", data=_valid_fields(token))
    assert r.status_code == 200
    assert "Solicitação enviada com sucesso!" in r.text


def test_attachment_invalid_type_returns_422(client):
    token = _get_token(client)
    files = {"attachment": ("evil.exe", b"MZ\x90\x00", "application/x-msdownload")}
    r = client.post("/contato", data=_valid_fields(token), files=files)
    assert r.status_code == 422
    assert "não permitido" in r.text or "formato" in r.text.lower()


def test_attachment_oversized_returns_422(client):
    token = _get_token(client)
    big = b"x" * (20 * 1024 * 1024 + 1)
    files = {"attachment": ("big.pdf", big, "application/pdf")}
    r = client.post("/contato", data=_valid_fields(token), files=files)
    assert r.status_code == 422
    assert "grande" in r.text or "MB" in r.text


def test_attachment_valid_pdf_no_r2_succeeds(client):
    """When R2 is disabled, a valid file upload still persists (no R2 call)."""
    token = _get_token(client)
    files = {"attachment": ("brief.pdf", b"%PDF-1.4 content", "application/pdf")}
    r = client.post("/contato", data=_valid_fields(token), files=files)
    assert r.status_code == 200
    assert "Solicitação enviada com sucesso!" in r.text


def test_attachment_valid_pdf_with_r2_uploads(client, monkeypatch):
    monkeypatch.setattr(settings, "enable_object_storage", True, raising=False)
    monkeypatch.setattr(settings, "r2_endpoint_url", "https://r2.test", raising=False)
    monkeypatch.setattr(settings, "r2_access_key", "key", raising=False)
    monkeypatch.setattr(settings, "r2_secret_key", "secret", raising=False)
    monkeypatch.setattr(settings, "r2_bucket_name", "bucket", raising=False)
    monkeypatch.setattr(settings, "r2_public_url", "https://pub.test", raising=False)

    with patch("app.services.storage_service._upload_sync",
               return_value="https://pub.test/contact-attachments/abc_brief.pdf"):
        token = _get_token(client)
        files = {"attachment": ("brief.pdf", b"%PDF-1.4 content", "application/pdf")}
        r = client.post("/contato", data=_valid_fields(token), files=files)

    assert r.status_code == 200
    assert "Solicitação enviada com sucesso!" in r.text
```

- [ ] **Step 2: Run tests — expect FAIL**

```
.venv/bin/pytest tests/unit/test_contact_attachment.py -v
```

- [ ] **Step 3: Enable attachment field in site_content.py**

In `app/content/site_content.py`, change:
```python
    Field("attachment", "Anexar arquivo", kind="file", enabled=False,
```
to:
```python
    Field("attachment", "Anexar arquivo", kind="file", enabled=True,
```

- [ ] **Step 4: Update _field.html to render enabled file input**

In `templates/partials/_field.html`, change the file branch:

```jinja
{% elif f.kind == 'file' %}
  {% if f.enabled %}
  <input class="input-el {% if err %}input-el--error{% endif %}" id="f-{{ f.name }}"
         name="{{ f.name }}" type="file"
         aria-describedby="hint-{{ f.name }}">
  {% else %}
  <input class="input-el" id="f-{{ f.name }}" name="{{ f.name }}" type="file" disabled
         aria-describedby="hint-{{ f.name }}">
  <p class="input-hint" id="hint-{{ f.name }}">Envio de anexos disponível em breve.</p>
  {% endif %}
```

- [ ] **Step 5: Add multipart enctype to contact_form.html**

In `templates/partials/contact_form.html`, change the `<form>` tag:

```html
<form id="contact-form" class="form" method="post" action="/contato"
      enctype="multipart/form-data"
      hx-post="/contato" hx-target="#contato-panel" hx-swap="innerHTML"
      hx-encoding="multipart/form-data" novalidate>
```

- [ ] **Step 6: Add attachment constants and wiring to contact.py**

At the top of `app/routers/contact.py`, add the constants:

```python
CONTACT_ALLOWED_TYPES = frozenset({
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "image/png",
    "image/jpeg",
    "application/zip",
})
CONTACT_MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024  # 20 MB
```

Update `_persist` to accept and store attachment fields:

```python
async def _persist(
    submission: ContactSubmission,
    db,
    attachment_url: str | None = None,
    attachment_key: str | None = None,
) -> None:
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
            contact_preference=submission.contact_preference,
            best_time=submission.best_time,
            attachment_url=attachment_url,
            attachment_key=attachment_key,
        )
        db.add(msg)
        await db.commit()
    elif settings.enable_database:
        if settings.environment == "production":
            raise RuntimeError("Database unavailable; cannot persist contact message.")
        get_contact_sink(settings).save(submission)
    else:
        get_contact_sink(settings).save(submission)
```

Add attachment handling to `submit_contact` after step 4 (Validate) and before step 5 (Persist):

```python
    # 4.5) Handle optional attachment
    attachment_url: str | None = None
    attachment_key: str | None = None
    attachment_field = form.get("attachment")
    if attachment_field is not None and hasattr(attachment_field, "read"):
        file_bytes = await attachment_field.read()
        if file_bytes:
            content_type = (attachment_field.content_type or "").split(";")[0].strip()
            if content_type not in CONTACT_ALLOWED_TYPES:
                return _render_form(
                    request, values=values,
                    errors={"attachment": "Formato de arquivo não permitido. Use PDF, DOCX, XLSX, CSV, PNG, JPG ou ZIP."},
                    status_code=422,
                )
            if len(file_bytes) > CONTACT_MAX_ATTACHMENT_BYTES:
                return _render_form(
                    request, values=values,
                    errors={"attachment": f"Arquivo muito grande. Máximo 20 MB."},
                    status_code=422,
                )
            if settings.enable_object_storage:
                from app.services.storage_service import upload_to_r2
                try:
                    attachment_url, attachment_key = await upload_to_r2(
                        file_bytes=file_bytes,
                        folder="contact-attachments",
                        filename=attachment_field.filename or "attachment",
                        content_type=content_type,
                        allowed_types=CONTACT_ALLOWED_TYPES,
                        max_size=CONTACT_MAX_ATTACHMENT_BYTES,
                    )
                except ValueError as exc:
                    return _render_form(
                        request, values=values,
                        errors={"attachment": str(exc)},
                        status_code=422,
                    )
```

Update the persist call:

```python
    # 5) Persist
    try:
        await _persist(submission, db, attachment_url=attachment_url, attachment_key=attachment_key)
    except Exception:
        ...
```

- [ ] **Step 7: Run attachment tests — expect PASS**

```
.venv/bin/pytest tests/unit/test_contact_attachment.py -v
```

- [ ] **Step 8: Run full suite**

```
.venv/bin/pytest -q
```

---

### Task 5: Admin password hashing in UserAdmin

**Files:**
- Modify: `app/admin/views.py`
- Test: `tests/unit/test_admin_views.py` (new)

**Interfaces:**
- `UserAdmin.on_model_change(data, model, is_created, request)` hashes `data["password"]` when non-empty

- [ ] **Step 1: Create test file**

```python
# tests/unit/test_admin_views.py
"""UserAdmin must hash passwords, never store plaintext."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.security import verify_password


@pytest.mark.anyio
async def test_user_admin_hashes_password_on_create():
    from app.admin.views import UserAdmin
    data = {"username": "admin", "email": "a@b.com", "password": "plain-secret"}
    view = UserAdmin()
    await view.on_model_change(data, model=None, is_created=True, request=MagicMock())
    assert data["password"] != "plain-secret"
    assert verify_password("plain-secret", data["password"])


@pytest.mark.anyio
async def test_user_admin_hashes_password_on_edit():
    from app.admin.views import UserAdmin
    existing_hash = "$argon2id$v=19$m=65536,t=3,p=4$fakehash"
    model = MagicMock()
    model.password = existing_hash
    data = {"username": "admin", "email": "a@b.com", "password": "new-secret"}
    view = UserAdmin()
    await view.on_model_change(data, model=model, is_created=False, request=MagicMock())
    assert data["password"] != "new-secret"
    assert verify_password("new-secret", data["password"])


@pytest.mark.anyio
async def test_user_admin_preserves_existing_hash_when_password_blank():
    from app.admin.views import UserAdmin
    existing_hash = "$argon2id$v=19$m=65536,t=3,p=4$fakehash"
    model = MagicMock()
    model.password = existing_hash
    data = {"username": "admin", "email": "a@b.com", "password": ""}
    view = UserAdmin()
    await view.on_model_change(data, model=model, is_created=False, request=MagicMock())
    assert data["password"] == existing_hash


@pytest.mark.anyio
async def test_user_admin_preserves_existing_hash_when_password_none():
    from app.admin.views import UserAdmin
    existing_hash = "$argon2id$v=19$m=65536,t=3,p=4$fakehash"
    model = MagicMock()
    model.password = existing_hash
    data = {"username": "admin", "email": "a@b.com", "password": None}
    view = UserAdmin()
    await view.on_model_change(data, model=model, is_created=False, request=MagicMock())
    assert data["password"] == existing_hash
```

- [ ] **Step 2: Run test — expect FAIL**

```
.venv/bin/pytest tests/unit/test_admin_views.py -v
```

- [ ] **Step 3: Add on_model_change to UserAdmin**

In `app/admin/views.py`, add inside `UserAdmin` class after `form_excluded_columns`:

```python
    async def on_model_change(self, data, model, is_created, request):
        from app.core.security import get_password_hash
        password = (data.get("password") or "").strip()
        if password:
            data["password"] = get_password_hash(password)
        elif not is_created and model is not None:
            data["password"] = model.password
```

- [ ] **Step 4: Run test — expect PASS**

```
.venv/bin/pytest tests/unit/test_admin_views.py -v
```

- [ ] **Step 5: Run full suite**

```
.venv/bin/pytest -q
```

---

### Task 6: Final verification

- [ ] **Step 1: Install anyio if needed**

Check `pyproject.toml`. If `anyio` is missing from dev deps, run:
```
.venv/bin/pip install anyio[trio]
```
And add to `pyproject.toml` dev section: `"anyio[trio]>=4.4"`.

- [ ] **Step 2: Run pytest --collect-only to count tests**

```
.venv/bin/pytest --collect-only -q 2>&1 | tail -5
```
Expected: ≥70 tests collected

- [ ] **Step 3: Run full suite**

```
.venv/bin/pytest -q
```
Expected: all pass

- [ ] **Step 4: Compile check**

```
.venv/bin/python -m compileall app tests -q
```

- [ ] **Step 5: git diff --check**

```
git diff --check
```

- [ ] **Step 6: Report exact results**

Record test count, pass count, any warnings.
