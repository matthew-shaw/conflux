# Stage 1: Build static web assets
FROM node:krypton-alpine AS web-builder

WORKDIR /web

COPY web/.browserslistrc web/eslint.config.mjs web/package*.json web/webpack.config.js ./
COPY web/src src

RUN npm install && \
    npm run build

# Stage 2: Build the Python environment
FROM python:3.14-slim AS builder

# Install uv and build dependencies only here
COPY --from=ghcr.io/astral-sh/uv:0.12.22 /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /home/appuser

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev


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

# Install Python packages from the uv-managed environment
COPY --from=builder --chown=appuser:0 /home/appuser/.venv .venv

# Copy application code
COPY --chown=appuser:0 conflux.py config.py ./ 
COPY --chown=appuser:0 app app
COPY --chown=appuser:0 migrations migrations

COPY --from=web-builder --chown=appuser:0 /web/dist app/static

# Copy entrypoint script into PATH
COPY --chown=appuser:0 docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER appuser

ENTRYPOINT ["docker-entrypoint.sh"]
