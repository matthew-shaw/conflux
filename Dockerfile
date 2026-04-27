# Stage 1: Build static web assets
FROM node:krypton-alpine AS web-builder

WORKDIR /web

COPY web/.browserslistrc web/eslint.config.mjs web/package*.json web/webpack.config.js ./
COPY web/src src

RUN npm install && \
    npm run build

# Stage 2: Build Python wheels
FROM python:3.14-slim AS builder

# Install build dependencies only here
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
# Build wheels instead of direct install
RUN pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels


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
    PYTHONUNBUFFERED=1

WORKDIR /home/appuser

# Install Python packages from wheels
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

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
