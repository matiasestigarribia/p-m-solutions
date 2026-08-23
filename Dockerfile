# P & M Solutions — MVP image.
# Binds to $PORT, runs as non-root, includes all dependencies for
# Neon PostgreSQL (asyncpg), Cloudflare R2 (boto3), Pillow, and SQLAdmin.
# No chatbot / LLM libraries.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

# Build deps for asyncpg (C extension) and Pillow
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip \
    && pip install \
        "fastapi>=0.115" \
        "uvicorn[standard]>=0.30" \
        "jinja2>=3.1" \
        "pydantic>=2.7" \
        "pydantic-settings>=2.3" \
        "email-validator>=2.1" \
        "itsdangerous>=2.2" \
        "python-multipart>=0.0.9" \
        "sqlalchemy[asyncio]>=2.0" \
        "asyncpg>=0.29" \
        "alembic>=1.13" \
        "sqladmin>=0.19" \
        "PyJWT>=2.8" \
        "pwdlib[argon2]>=0.2" \
        "boto3>=1.34" \
        "pillow>=10.3"

COPY app ./app
COPY templates ./templates
COPY static ./static
COPY migrations ./migrations
COPY alembic.ini ./

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c \
        "import os,urllib.request; \
         urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8080')+'/health').read()" \
    || exit 1

# Cloud Run injects $PORT at runtime.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers"]
