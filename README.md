# P & M Solutions — MVP

Public content site with Neon PostgreSQL persistence, Cloudflare R2 media,
SQLAdmin, and an HTMX/Jinja2 frontend. Chatbot / LLM / vector search are
intentionally absent from this release.

> **External accounts are not provisioned by this repository.**
> You must create your own Neon project and Cloudflare R2 bucket.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI 0.115+, Python 3.13 |
| Database | Neon PostgreSQL (asyncpg) + pgvector extension |
| ORM / Migrations | SQLAlchemy 2.0 (async) + Alembic |
| Admin | SQLAdmin (authenticated, JWT sessions) |
| Storage | Cloudflare R2 (S3-compatible, async via boto3) |
| Auth | JWT + Argon2 (pwdlib) |
| Frontend | HTMX, Jinja2, custom CSS |
| Container | Docker (non-root, PORT-bound) |
| Package manager | uv |

---

## External Services Required

| Service | Purpose | Free tier? |
|---|---|---|
| [Neon](https://neon.tech) | Serverless PostgreSQL | Yes |
| [Cloudflare R2](https://developers.cloudflare.com/r2/) | Object storage (product media, attachments) | Yes (10 GB) |

---

## Getting Started

### 1. Clone and install

```bash
git clone <repo-url>
cd p-m-solutions
uv venv .venv
uv pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — fill in credentials and set PM_ENABLE_DATABASE=true
```

### 3. Enable pgvector on Neon

In the Neon SQL editor (or via psql):

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

> This is the MVP foundation. No vector columns are created by this migration.

### 4. Run database migrations

```bash
PM_DATABASE_URL=postgresql+asyncpg://... .venv/bin/alembic upgrade head
```

### 5. Create the first admin user

```python
# create_admin.py — do not commit; add to .gitignore
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_engine
from app.core.security import get_password_hash
from app.models.users import User

async def main():
    async with AsyncSession(get_engine()) as session:
        user = User(
            username="admin",
            email="your@email.com",
            password=get_password_hash("YourStrongPassword!"),
        )
        session.add(user)
        await session.commit()
    print("Admin user created.")

asyncio.run(main())
```

```bash
PM_DATABASE_URL=... PM_ENABLE_DATABASE=true python create_admin.py
```

### 6. Run locally

```bash
PM_ENABLE_DATABASE=true PM_DATABASE_URL=... uvicorn app.main:app --reload
```

- Site: `http://localhost:8000`
- Admin: `http://localhost:8000/admin`
- Health: `http://localhost:8000/health`

### 7. Seed approved content

The approved Company, Mission, Vision, and Purpose copy is seeded into Neon
with the local, Git-ignored operational script:

```bash
.venv/bin/python scripts/seed_cms.py
```

Production requires those CMS rows. Products remain empty until approved
product names and descriptions are supplied; the public site shows its honest
empty state rather than fabricated content.

---

## Running with Docker

```bash
docker build -t pm-solutions .
docker run -p 8080:8080 --env-file .env pm-solutions
```

---

## Running Tests

```bash
.venv/bin/pytest -q
# Collect only (dry run):
.venv/bin/pytest --collect-only -q
```

Tests do **not** require real Neon or R2 credentials. DB routes are tested
with `PM_ENABLE_DATABASE=false` (site_content fallback). R2 is mocked.

---

## Cloud Run Deployment

```bash
# Build and push
docker build -t gcr.io/PROJECT/pm-solutions .
docker push gcr.io/PROJECT/pm-solutions

# Deploy
gcloud run deploy pm-solutions \
  --image gcr.io/PROJECT/pm-solutions \
  --region us-central1 \
  --set-env-vars PM_ENVIRONMENT=production \
  --set-secrets PM_SECRET_KEY=pm-secret-key:latest \
  --set-secrets PM_ADMIN_SECRET_KEY=pm-admin-secret-key:latest \
  --set-secrets PM_DATABASE_URL=pm-database-url:latest \
  --set-env-vars PM_ENABLE_DATABASE=true \
  --set-secrets PM_R2_ACCESS_KEY=pm-r2-access-key:latest \
  --set-secrets PM_R2_SECRET_KEY=pm-r2-secret-key:latest \
  --set-env-vars PM_R2_ENDPOINT_URL=https://... \
  --set-env-vars PM_R2_BUCKET_NAME=pm-solutions \
  --set-env-vars PM_R2_PRIVATE_BUCKET_NAME=pm-solutions-private \
  --set-env-vars PM_R2_PUBLIC_URL=https://assets.yourdomain.com \
  --set-env-vars PM_ENABLE_OBJECT_STORAGE=true
```

After deploy, run migrations:
```bash
# One-off Cloud Run job
gcloud run jobs create pm-migrate \
  --image gcr.io/PROJECT/pm-solutions \
  --command alembic \
  --args upgrade,head \
  --set-secrets PM_DATABASE_URL=pm-database-url:latest \
  --set-env-vars PM_ENABLE_DATABASE=true
gcloud run jobs execute pm-migrate
```

### Rollback

```bash
# Deploy previous revision
gcloud run services update-traffic pm-solutions --to-revisions PREVIOUS_REVISION=100

# Rollback DB (use with care — only if downgrade is safe)
PM_DATABASE_URL=... .venv/bin/alembic downgrade -1
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `PM_SECRET_KEY` | **Production** | CSRF + admin JWT signing key |
| `PM_ENVIRONMENT` | No | `development` / `staging` / `production` |
| `PM_ENABLE_DATABASE` | Yes (prod) | `true` to activate Neon |
| `PM_DATABASE_URL` | When DB enabled | `postgresql+asyncpg://...?ssl=require` |
| `PM_ADMIN_SECRET_KEY` | **Production** | Separate JWT key for admin sessions (minimum 32 characters) |
| `PM_ENABLE_OBJECT_STORAGE` | No | `true` to activate R2 |
| `PM_R2_ENDPOINT_URL` | When R2 enabled | Cloudflare R2 endpoint |
| `PM_R2_ACCESS_KEY` | When R2 enabled | R2 access key ID |
| `PM_R2_SECRET_KEY` | When R2 enabled | R2 secret access key |
| `PM_R2_BUCKET_NAME` | When R2 enabled | Bucket name |
| `PM_R2_PRIVATE_BUCKET_NAME` | When R2 enabled | Private bucket for contact attachments |
| `PM_R2_PUBLIC_URL` | When R2 enabled | Public base URL for R2 assets |

---

## Admin Panel

`/admin` — login with admin user credentials.

| Section | Description |
|---|---|
| Users | Admin user management |
| Company | "Quem Somos" page copy |
| Mission | Missão copy |
| Vision | Visão copy |
| Purpose | Propósito copy |
| Products | Product cards (name, description, optional R2 image) |
| Contact Messages | Submitted contact forms |

---

## Project Structure

```
p-m-solutions/
├── app/
│   ├── admin/          # SQLAdmin + JWT auth backend
│   ├── content/        # Verbatim stakeholder copy (site_content.py)
│   ├── core/           # Settings, DB engine, security, templating
│   ├── models/         # SQLAlchemy ORM models
│   ├── routers/        # FastAPI routes (pages + contact)
│   ├── schemas/        # Pydantic schemas
│   └── services/       # R2 storage, image optimisation, contact sink
├── migrations/         # Alembic scripts
│   └── versions/
├── static/             # CSS, JS, images
├── templates/          # Jinja2 templates (HTMX fragments)
├── tests/
│   ├── integration/
│   └── unit/
├── alembic.ini
├── Dockerfile
├── pyproject.toml
└── .env.example
```
