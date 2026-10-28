#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"

echo "=========================================================="
echo " Starting Evidra Systematic Literature Review Engine"
echo " Environment: ${APP_ENV:-production}  Auth: ${AUTH_MODE:-local}  Port: ${PORT}"
echo " Data Directory: ${DATA_DIR:-/app/data}"
echo "=========================================================="

cd /app/backend

# --no-dev: the image only contains runtime dependencies; never install test tools at start-up
UV_RUN=(uv run --locked --no-dev)

# 1. Run linear Alembic database migrations
echo "[1/4] Running database migrations (alembic upgrade head)..."
"${UV_RUN[@]}" alembic upgrade head

# 2. Check disk space and readiness
echo "[2/4] Verifying persistent storage directory..."
mkdir -p "${DATA_DIR:-/app/data}/models"
mkdir -p "${DATA_DIR:-/app/data}/backups"

# 3. Optionally load the synthetic demo review (only if it isn't there already)
if [[ "${SEED_DEMO:-false}" == "true" ]]; then
  echo "[3/4] Loading the demo review if missing..."
  "${UV_RUN[@]}" python scripts/seed_demo.py
else
  echo "[3/4] SEED_DEMO is not 'true'; skipping demo data."
fi

# 4. Start Uvicorn HTTP server
echo "[4/4] Launching FastAPI application on 0.0.0.0:${PORT}..."
exec "${UV_RUN[@]}" uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --workers "${WORKERS:-1}" --proxy-headers --forwarded-allow-ips="*"
