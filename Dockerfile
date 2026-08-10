# P & M Solutions — Stage 1 image.
# Builds a small content-site + contact-form service ready for Cloud Run.
# Binds to $PORT, runs as a non-root user, and installs ONLY Stage 1 deps
# (no Neon/R2/chatbot libraries).
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

# Install runtime dependencies first (better layer caching). Only pyproject is
# needed to resolve the Stage 1 dependency set.
COPY pyproject.toml ./
RUN pip install --upgrade pip \
    && pip install "fastapi>=0.115" "uvicorn[standard]>=0.30" "jinja2>=3.1" \
        "pydantic>=2.7" "pydantic-settings>=2.3" "email-validator>=2.1" \
        "itsdangerous>=2.2" "python-multipart>=0.0.9"

# Application source (respecting .dockerignore: no _reference/, no secrets,
# no local SQLite, no venv).
COPY app ./app
COPY templates ./templates
COPY static ./static

# Writable data dir for the local SQLite contact sink (ephemeral on Cloud Run —
# see NOTE below). Owned by the non-root user.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Cloud Run injects $PORT; default to 8080 locally.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8080')+'/health').read()" || exit 1

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers"]

# NOTE (Stage 2): Cloud Run's filesystem is ephemeral and per-instance. The
# local SQLite contact sink is fine for a single-instance Stage 1 deployment,
# but submissions do NOT persist across revisions/instances. Stage 2 replaces
# the sink with Neon PostgreSQL via app/services/integrations.get_database.
