# Multi-stage production deployment container for Evidra (A06)
# Stage 1: Build React SPA
FROM node:24-alpine AS frontend-builder
WORKDIR /build/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
COPY contracts/ ../contracts/
RUN npm run build

# Stage 2: Python / FastAPI backend runtime
FROM python:3.12-slim AS runtime

# System dependencies: SQLite 3 and curl for health probes
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:0.5.26 /uv /uvx /bin/

WORKDIR /app

# Install backend dependencies
COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN cd backend && uv sync --frozen --no-dev

# Copy backend source and migrations
COPY backend/ ./backend/
COPY contracts/ ./contracts/

# Copy built frontend assets
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

# Persistent data directory
RUN mkdir -p /app/data && chmod 777 /app/data
ENV DATA_DIR=/app/data \
    DATABASE_URL=sqlite:////app/data/review.sqlite \
    CHECKPOINT_DATABASE_URL=sqlite:////app/data/checkpoints.sqlite \
    FRONTEND_DIST=/app/frontend/dist \
    APP_ENV=production \
    AUTH_MODE=local \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Copy and setup entrypoint
COPY infra/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
