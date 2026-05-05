# syntax=docker/dockerfile:1.7
# ─────────────────────────────────────────────────────────────────────────────
# NEXUS Precon backend — production image (Phase 7.3)
#
# Multi-stage build keeps the runtime image small by leaving build toolchains
# behind in the builder.  Runtime ships:
#   * python:3.12-slim
#   * a virtualenv at /opt/venv with the OCERP + precon deps baked in
#   * the OCERP `backend/` source at /app
#   * a non-root ``app`` user
#   * curl for the healthcheck (FastAPI app exposes /api/health)
#
# Build context: repo root.  The existing repo-root .dockerignore already
# excludes node_modules, frontend builds, .git, .claude, *.db, secrets, etc.
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: builder ────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=180

# System build deps.  ``psycopg2-binary`` ships precompiled wheels so
# libpq-dev is not strictly required, but build-essential is needed for
# the few wheels that fall through to source compilation on slim images.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Use an isolated virtualenv so the runtime stage can copy a single tree.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install the OCERP backend with the [server] extra.  pyproject.toml
# declares asyncpg + psycopg2-binary + celery[redis] + boto3 under
# [server], which is what we need for the Railway Postgres + Redis stack.
WORKDIR /build
COPY backend/pyproject.toml backend/README.md ./
# Copy minimal source needed for the install (pyproject targets the
# ``app`` package).  The runtime stage re-copies app/ as a fresh layer.
COPY backend/app ./app

# pyproject.toml force-includes ``../frontend/dist`` for the openestimate
# CLI that bundles the React build into the wheel.  Backend-only Railway
# images don't serve the frontend (Vercel does), so we satisfy hatchling
# with an empty placeholder directory rather than dragging the entire
# frontend build through this stage.
RUN mkdir -p /frontend/dist \
    && touch /frontend/dist/.placeholder

RUN pip install --upgrade pip \
    && pip install --no-cache-dir ".[server,vector]"


# ── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000

# curl: container healthcheck.  ca-certificates: outbound TLS for the
# (future) GovTribe MCP HTTP transport.  No build tools.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --home-dir /app --shell /bin/sh app

# Bring in the venv from the builder.
COPY --from=builder /opt/venv /opt/venv

# Application code.
WORKDIR /app
COPY backend/app ./app
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
# Strip CRLF defensively — protects against build contexts assembled on
# Windows hosts (e.g. `railway up`) where core.autocrlf may have rewritten
# the file to CRLF in the working tree, breaking the shebang at runtime
# with: /usr/bin/env: 'sh\r': No such file or directory
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh \
    && chown -R app:app /app

USER app

EXPOSE 8000

# Container-level healthcheck — Railway also probes via its own healthcheck
# config, but having it baked in lets ``docker ps`` show health status for
# local builds and any non-Railway runtimes.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl --fail --silent --show-error \
        "http://127.0.0.1:${PORT:-8000}/api/health" \
        || exit 1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
