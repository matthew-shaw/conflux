# Stage 1: Build static web assets
FROM node:krypton-alpine AS web-builder

WORKDIR /web

COPY web/.browserslistrc web/eslint.config.mjs web/package*.json web/webpack.config.js ./
COPY web/src src

RUN npm install && \
    npm run build


# Stage 2: Build Python environment
FROM python:3.14-slim AS app-builder

# Pin uv to the version used by the project.
COPY --from=ghcr.io/astral-sh/uv:0.12.22 /uv /uvx /bin/

# Use the Python already provided by the base image.
ENV UV_PYTHON_DOWNLOADS=0 \
    UV_LINK_MODE=copy

# Build dependencies required for packages such as psycopg2.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only dependency metadata first.
# This keeps the dependency layer highly cacheable.
COPY pyproject.toml uv.lock .python-version ./

# Create a production-only virtual environment.
#
# --locked       Fail if uv.lock is out of date.
# --no-dev       Exclude the development dependency group.
# --no-install-project
#                Don't install Conflux itself.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync \
    --locked \
    --no-dev \
    --no-install-project


# Stage 3: Final runtime image
FROM python:3.14-slim

# Install only runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN adduser --system --group appuser

ENV FLASK_APP=conflux.py \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.venv/bin:$PATH"

WORKDIR /home/appuser

# Copy only the production virtual environment.
# Build tools, headers, uv, and the uv cache do not enter the runtime image.
COPY --from=app-builder \
    --chown=appuser:0 \
    /app/.venv \
    /home/appuser/.venv

# Copy application code
COPY --chown=appuser:0 conflux.py config.py ./
COPY --chown=appuser:0 app app
COPY --chown=appuser:0 migrations migrations

# Copy compiled frontend assets
COPY --from=web-builder \
    --chown=appuser:0 \
    /web/dist \
    app/static

# Copy entrypoint script
COPY --chown=appuser:0 docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER appuser

ENTRYPOINT ["docker-entrypoint.sh"]