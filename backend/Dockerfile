# ---------------------------------------------------------------------
# Backend Dockerfile — Flask API + ML pipeline
# ---------------------------------------------------------------------
FROM python:3.11-slim AS base

# System deps needed by lightgbm/xgboost/catboost (libgomp) and mysqlclient build
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    gcc \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY config/ ./config/
COPY backend/ ./backend/
COPY dataset/ ./dataset/

# Models are trained separately and mounted/copied in (see docker-compose volume)
RUN mkdir -p models/saved research/reports research/shap backend/logs

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120", "backend.app:create_app()"]
