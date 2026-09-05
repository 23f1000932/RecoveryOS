# RecoveryOS — Backend Dockerfile
#
# Builds a minimal Python 3.12 image for the FastAPI backend.
# Intended for deployment on Render.com.
#
# Build:
#   docker build -t recoveryos .
#
# Run locally:
#   docker run -p 8000:8000 --env-file .env recoveryos
#
# Environment variables required at runtime:
#   DATABASE_URL
#   GEMINI_API_KEY
#   RAZORPAY_KEY_ID
#   RAZORPAY_KEY_SECRET
#   RAZORPAY_WEBHOOK_SECRET
#   ENVIRONMENT (production | staging | development)

FROM python:3.12-slim AS base

# System dependencies (asyncpg needs libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Install Python dependencies ────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Copy source ────────────────────────────────────────────────────────────────
# Copy only what the backend needs; excludes .venv, .git, frontend, tests
COPY backend/ ./backend/
COPY ml/ ./ml/
COPY simulator/ ./simulator/
COPY policies/ ./policies/

# ── Train ML models at build time (survives gitignore per Phase 3) ─────────────
RUN python -m ml.train --rows 50000 --seed 42

# ── Health check ───────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# ── Runtime ────────────────────────────────────────────────────────────────────
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
