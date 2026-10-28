#!/usr/bin/env bash
set -euo pipefail

echo "=========================================================="
echo " Starting Evidra Systematic Literature Review Engine"
echo " Environment: ${APP_ENV:-production}"
echo " Data Directory: ${DATA_DIR:-/app/data}"
echo "=========================================================="

cd /app/backend

# 1. Run linear Alembic database migrations
echo "[1/3] Running database migrations (alembic upgrade head)..."
uv run --locked alembic upgrade head

# 2. Check disk space and readiness
echo "[2/3] Verifying persistent storage directory..."
mkdir -p "${DATA_DIR:-/app/data}/models"
mkdir -p "${DATA_DIR:-/app/data}/backups"

# 3. Start Uvicorn HTTP server
echo "[3/3] Launching FastAPI application on 0.0.0.0:8000..."
exec uv run --locked uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${WORKERS:-2}"
