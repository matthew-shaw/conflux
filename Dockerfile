FROM python:3.13-slim

RUN addgroup --system appgroup && adduser --system --group appuser

# Install build dependencies (e.g., gcc, postgresql-dev, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV FLASK_APP=mimir.py \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /home/appuser

COPY --chown=appuser:appgroup mimir.py config.py requirements.txt ./

RUN pip install -r requirements.txt

COPY --chown=appuser:appgroup app app

USER appuser

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "-w", "4", "--access-logfile", "-", "mimir:app"]