# ── UrbanPulse API — Dockerfile ──────────────────────────────────────────────
# Base: python:3.11-slim for a small production image.
# Copies only the backend/ directory and the project-level data/, models/,
# and scripts/ directories required at runtime.
# Runs uvicorn on port 8000 (non-root user).

FROM python:3.11-slim

# ── System dependencies (psycopg2-binary ships its own libpq, so only
#    build tools needed for any packages that might compile C extensions) ──────
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user for security ────────────────────────────────────────────────
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/urbanpulse

# ── Install Python dependencies ───────────────────────────────────────────────
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Copy application source ───────────────────────────────────────────────────
# backend/ source
COPY backend/ ./backend/

# Trained ML model artifacts (must exist on host before docker build)
COPY models/ ./models/

# Synthetic + processed data (city_master.csv needed at startup)
COPY data/synthetic/ ./data/synthetic/
COPY data/processed/ ./data/processed/

# ── Ownership ─────────────────────────────────────────────────────────────────
RUN chown -R appuser:appuser /home/appuser/urbanpulse
USER appuser

# ── Environment defaults (override via docker run -e or docker-compose) ───────
ENV DATABASE_URL="postgresql://localhost/urbanpulse"
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/home/appuser/urbanpulse/backend"

# ── Port + health check ───────────────────────────────────────────────────────
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# ── Entrypoint ────────────────────────────────────────────────────────────────
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]