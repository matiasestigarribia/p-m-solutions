# P&M Solutions MVP — Neon + R2 + Content Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Activate full MVP public site with Neon PostgreSQL persistence, Cloudflare R2 media, authenticated SQLAdmin panel, and DB-backed content for Company/Mission/Vision/Purpose/Products/ContactMessages — ready for Cloud Run, no chatbot.

**Architecture:** Lazy async SQLAlchemy engine (PgBouncer-safe) guarded by `settings.enable_database`; content proxy pattern so templates see `content.X` regardless of source; conditional admin mount; dev falls back to site_content.py when DB disabled.

**Tech Stack:** FastAPI, SQLAlchemy 2 (async) + asyncpg, Alembic + pgvector extension, SQLAdmin, PyJWT, pwdlib[argon2], boto3 (R2), Pillow, itsdangerous (CSRF — existing), uv.

## Global Constraints
- `PM_` env prefix on all new settings fields
- Neon URL: `postgresql+asyncpg://...?ssl=require`; `connect_args={"statement_cache_size": 0}` for PgBouncer
- No chatbot, no LLM, no langchain, no embeddings, no pgvector runtime usage
- Initial migration: `CREATE EXTENSION IF NOT EXISTS vector` (foundation only)
- No secrets in code or logs
- All templates stay unchanged (content proxy pattern)
- Verbatim copy in site_content.py is sacrosanct
- Non-root Docker image; PORT-bound; health pings DB when enabled
- Tests must not require real Neon/R2 credentials; use mocks and report

---

## File Map

### Create
- `app/core/database.py` — lazy async engine singleton, get_session, get_engine
- `app/models/base.py` — DeclarativeBase
- `app/models/__init__.py` — re-export all models for Alembic
- `app/models/users.py` — User (admin auth)
- `app/models/company.py` — Company/Quem Somos
- `app/models/mission.py` — Mission
- `app/models/vision.py` — Vision
- `app/models/purpose.py` — Purpose
- `app/models/products.py` — Product with R2 media
- `app/models/contact_messages.py` — ContactMessage with all qualification fields
- `app/schemas/company.py` — Pydantic schemas for content entities
- `app/schemas/products.py` — Product schemas
- `app/schemas/contact_messages.py` — ContactMessage DB schemas
- `app/admin/__init__.py` — empty
- `app/admin/admin.py` — UrlAwareAdmin (file-upload fix)
- `app/admin/auth.py` — AdminAuth (JWT sessions)
- `app/admin/views.py` — ModelView for all P&M entities
- `app/services/storage_service.py` — R2 async adapter
- `app/services/image_service.py` — Pillow optimization
- `alembic.ini`
- `migrations/env.py`
- `migrations/README`
- `migrations/script.py.mako`
- `migrations/versions/a1b2c3d4e5f6_initial_schema.py`
- `.env.example`
- `README.md`
- `tests/unit/test_entity_schemas.py`
- `tests/unit/test_storage_service.py`
- `tests/unit/test_migration_structure.py`
- `tests/integration/test_admin_auth.py`

### Modify
- `pyproject.toml` — add core deps (sqlalchemy, asyncpg, alembic, sqladmin, boto3, pillow, pyjwt, pwdlib)
- `app/core/settings.py` — add database_url, admin JWT, R2 fields (all optional)
- `app/core/security.py` — add JWT + password hashing functions
- `app/main.py` — conditional DB/admin mount, DB-backed health
- `app/routers/pages.py` — DB-backed content reads with site_content fallback
- `app/routers/contact.py` — DB-backed contact persistence when enabled
- `app/services/integrations.py` — update to return real session factory when enabled
- `Dockerfile` — full deps + pgvector/asyncpg build deps
- `tests/unit/test_settings.py` — update for new optional fields
- `tests/unit/test_integrations.py` — update heavy-dep check (remove sqlalchemy/boto3, keep langchain)
- `tests/integration/test_site.py` — update health check assertions

---

### Task 1: pyproject.toml + settings + database

Files: `pyproject.toml`, `app/core/settings.py`, `app/core/database.py`

### Task 2: security.py additions

Files: `app/core/security.py`

### Task 3: Models

Files: `app/models/base.py`, `app/models/__init__.py`, `app/models/users.py`, `app/models/company.py`, `app/models/mission.py`, `app/models/vision.py`, `app/models/purpose.py`, `app/models/products.py`, `app/models/contact_messages.py`

### Task 4: Schemas

Files: `app/schemas/company.py`, `app/schemas/products.py`, `app/schemas/contact_messages.py`

### Task 5: Admin layer

Files: `app/admin/__init__.py`, `app/admin/admin.py`, `app/admin/auth.py`, `app/admin/views.py`

### Task 6: Storage + image services

Files: `app/services/storage_service.py`, `app/services/image_service.py`, `app/services/integrations.py`

### Task 7: Router + main.py updates

Files: `app/routers/pages.py`, `app/routers/contact.py`, `app/main.py`

### Task 8: Migrations

Files: `alembic.ini`, `migrations/env.py`, `migrations/README`, `migrations/script.py.mako`, `migrations/versions/a1b2c3d4e5f6_initial_schema.py`

### Task 9: Dockerfile + env + README

Files: `Dockerfile`, `.env.example`, `README.md`

### Task 10: Tests

Files: all test files
