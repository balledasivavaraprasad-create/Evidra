# Evidra Operations and Reliability Runbook

This document details production operations, database lifecycle, quiescent backup/restore procedures, security hardening, and deployment specifications for the Evidra Systematic Literature Review Engine (prepared by dev-D in D06 for release packaging in A06).

---

## 1. Process Topology and Runtime Architecture

Evidra operates as a decoupled, deterministic-first systematic review system:

```
[ Web Browser Client ]
          │ (REST / JSON / SSE)
          ▼
[ FastAPI Backend Process ] (uvicorn app.main:app)
    ├── Engine 1: Business SQLite (review.sqlite, WAL Mode)
    │     ├── Immutable Corpus Snapshots & Group Mappings
    │     ├── Append-only Reviewer Decision Events
    │     └── PICO Unicode Code-Point Offsets
    ├── Engine 2: LangGraph Checkpoints (checkpoints.sqlite, WAL Mode)
    │     └── Resumable workflow interrupt checkpoints
    ├── Engine 3: In-Memory SQLite FTS5 Virtual Index (:memory:)
    │     └── Authorized corpus text chunk retrieval (RAG)
    └── External Adapters:
          ├── Literature: PubMed / Europe PMC (Rate-limited, default 3.0 req/s)
          └── Optional LLM Gateway: Mock or HTTPX Adapter (default-off, budget-capped)
```

### Persistence and File System Boundaries
- **Business Database:** `DATABASE_URL=sqlite:////app/data/review.sqlite`
- **Checkpoint Database:** `CHECKPOINT_DATABASE_URL=sqlite:////app/data/checkpoints.sqlite`
- **Data & Artifacts Directory:** `DATA_DIR=/app/data` (must be mounted on a persistent volume)
- **Trained Classical ML Artifacts:** `/app/data/models/` (SHA-256 verified)

---

## 2. Database Migrations and Lifecycle

Evidra uses Alembic for forward-only, strictly linear schema migrations.

### Commands
```bash
# Check current migration heads (must return exactly ONE head)
uv run --locked alembic heads

# Run forward migrations to latest schema head
uv run --locked alembic upgrade head

# Inspect current schema version
uv run --locked alembic current
```

### Invariants
1. **Single Linear Migration Head:** Branching or multiple heads in Alembic fail CI immediately.
2. **Non-Destructive Evolution:** Reviewer decisions, raw source payloads, and historical corpus revisions must never be deleted during migration.
3. **Fresh Install & Upgrade Parity:** A fresh database migrated with `alembic upgrade head` produces an identical DDL structure to incremental upgrades from `001_initial_schema`.

---

## 3. SQLite WAL-Safe Backup and Restore Runbook

Because SQLite WAL mode keeps uncommitted and uncheckpointed pages in `-wal` and `-shm` sidecar files, standard file copying (`cp` or `tar`) can result in corrupted backups. Evidra provides atomic, quiescent backups via `app.services.backup`.

### Automated Backup Execution
```python
from pathlib import Path
from app.services.backup import create_backup

# Creates a point-in-time snapshot of business and checkpoint databases
manifest = create_backup(
    backup_dir=Path("/app/data/backups/backup_20261028_093000"),
    note="Scheduled daily quiescent backup",
)
print(f"Backup completed. Checksum: {manifest.databases['primary'].sha256}")
```

### Backup Artifacts Produced
- `backup_manifest.json`: Cryptographic manifest containing format version, timestamp, SHA-256 hashes, byte sizes, and record count audit.
- `review.sqlite`: Standalone, self-contained SQLite business database file with all WAL pages safely flushed.
- `checkpoints.sqlite`: Standalone checkpoint database file.

### Restoration Procedure
```python
from pathlib import Path
from app.services.backup import restore_backup

# Restores and verifies physical integrity to an empty directory
result = restore_backup(
    backup_dir=Path("/app/data/backups/backup_20261028_093000"),
    target_dir=Path("/app/data"),
    overwrite=False, # Fail-safe against accidental overwrites
)
print("Restore successful:", result["restored_files"])
```

### Verification Steps Upon Restore
1. SHA-256 checksum validation against `backup_manifest.json`.
2. Physical page validation via SQLite `PRAGMA integrity_check;`.
3. Schema version verification via `SELECT version_num FROM alembic_version;`.

---

## 4. Operational Health and Readiness Probes

### Liveness Probe (`GET /health/live`)
- **Purpose:** Used by container orchestrators (Docker, Kubernetes) to verify process responsiveness.
- **Expected Status:** HTTP 200 OK
- **Sample Payload:**
  ```json
  {
    "status": "ok",
    "app": "Evidra Systematic Literature Review Engine",
    "version": "0.1.0",
    "env": "production"
  }
  ```

### Readiness Probe (`GET /health/ready`)
- **Purpose:** Verifies that the service is physically capable of serving traffic before routing requests.
- **Validation Steps:**
  1. Business SQLite connectivity: `SELECT 1;`.
  2. Alembic migration status check.
  3. Minimum disk space check: verifies at least 10 MB free on data volume.
- **Success Status:** HTTP 200 OK
  ```json
  {
    "status": "ready",
    "database": "connected",
    "migration_version": "002_review_services_schema",
    "disk_free_bytes": 104857600,
    "llm_enabled": false,
    "rag_enabled": false
  }
  ```
- **Failure Status:** HTTP 503 Service Unavailable (e.g., `DISK_SPACE_EXHAUSTED` or `SERVICE_UNAVAILABLE`).

---

## 5. Security Hardening and Environment Configuration

### Fail-Closed Production Validation
When `APP_ENV=production`:
1. `SECRET_KEY` must be explicitly configured and contain at least 32 characters. Default dev keys are rejected with a startup exception.
2. `AUTH_MODE=production` is required. `AUTH_MODE=local` is forbidden in production environments.
3. Outbound literature requests are rate-limited (`SOURCE_RATE_LIMIT_PER_SECOND=3.0`) to prevent IP bans from PubMed/Europe PMC.

### Environment Variable Specification

| Variable | Default | Production Value | Description |
|---|---|---|---|
| `APP_ENV` | `development` | `production` | Deployment mode |
| `SECRET_KEY` | *(insecure dev default)* | *(32+ char secret)* | Cryptographic signing secret |
| `AUTH_MODE` | `local` | `production` | Authentication provider mode |
| `DATABASE_URL` | `sqlite:///./review.sqlite` | `sqlite:////app/data/review.sqlite` | WAL business database path |
| `CHECKPOINT_DATABASE_URL` | `sqlite:///./checkpoints.sqlite` | `sqlite:////app/data/checkpoints.sqlite` | LangGraph checkpoint path |
| `DATA_DIR` | `./data` | `/app/data` | Persistent storage root |
| `SOURCE_RATE_LIMIT_PER_SECOND`| `3.0` | `3.0` | Outbound request pacing |
| `LLM_ENABLED` | `false` | `false` (default-off) | Enable optional LLM gateway |
| `RAG_ENABLED` | `false` | `false` (default-off) | Enable bounded corpus RAG |
| `LLM_MAX_BUDGET_CENTS` | `500` | `500` | Spend ceiling in cents ($5.00) |
| `CORS_ORIGINS` | `["http://localhost:5173", ...]` | `["https://app.evidra.example.com"]` | Authorized client origins |

---

## 6. Handoff Specification for dev-A (A06 Release Packaging)

### Container Requirements
- **Backend Base:** Python 3.12-slim with `uv` package manager.
- **Frontend Base:** Node.js 24 Alpine/slim with `npm`.
- **Exposed Ports:**
  - Backend API: `8000`
  - Frontend Preview/Production Server: `4173` (or `80` with Nginx reverse proxy)
- **Startup Entrypoints:**
  - Backend: `uv run --locked alembic upgrade head && uv run --locked uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2`
  - Frontend: `npm run build && npm run preview -- --host 0.0.0.0 --port 4173`
- **Volume Mount:** Mount persistent volume to `/app/data`.
- **Health Check Path:** `http://localhost:8000/health/ready` (interval: 15s, timeout: 5s, retries: 3).
