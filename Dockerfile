# P & M Solutions — MVP image.
# Binds to $PORT, runs as non-root, includes all dependencies for
# Neon PostgreSQL (asyncpg + pgvector), Cloudflare R2, Pillow, SQLAdmin,
# and the Groq-generation/local-vector public RAG chatbot.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    PM_EMBEDDING_CACHE_DIR=/app/model-cache

WORKDIR /app

# Build deps for asyncpg (C extension) and Pillow
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN pip install --upgrade pip uv \
    && uv sync --frozen --no-dev --no-install-project
ENV PATH="/app/.venv/bin:$PATH"

COPY app ./app
COPY scripts ./scripts
COPY templates ./templates
COPY static ./static
COPY migrations ./migrations
COPY alembic.ini ./

# Bake the local embedding model into the image so the first request does not
# download it from Hugging Face at runtime.
RUN mkdir -p /app/model-cache \
    && python scripts/preload_embedding_model.py

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
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*'"]
