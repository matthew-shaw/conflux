# Stage 1: Build dependencies and install Python packages
FROM python:3.13-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libpq-dev

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

# Stage 2: Final runtime image
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system appgroup && adduser --system --group appuser

ENV FLASK_APP=mimir.py \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /home/appuser

# Copy installed packages from builder
COPY --from=builder /usr/local /usr/local

# Copy application code
COPY --chown=appuser:appgroup mimir.py config.py ./
COPY --chown=appuser:appgroup app app
COPY --chown=appuser:appgroup migrations migrations

# Copy entrypoint script into PATH
COPY --chown=appuser:appgroup docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER appuser

ENTRYPOINT ["docker-entrypoint.sh"]
