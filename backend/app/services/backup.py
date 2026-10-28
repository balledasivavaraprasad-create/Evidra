"""SQLite WAL-safe backup and restore service for Evidra systematic review databases.

Coordinates quiescent backups of the primary business database and checkpoint store
using the SQLite Online Backup API (sqlite3.Connection.backup).
Preserves reviewer events, corpus snapshots, and WAL state.
"""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.settings import settings

logger = logging.getLogger(__name__)

BACKUP_MANIFEST_NAME = "backup_manifest.json"
BACKUP_FORMAT_VERSION = "1.0.0"


@dataclass
class DatabaseBackupMeta:
    """Metadata for an individual backed-up SQLite database."""
    name: str
    target_filename: str
    sha256: str
    byte_size: int
    schema_version: str | None
    integrity_ok: bool


@dataclass
class BackupManifest:
    """Top-level manifest describing an Evidra quiescent backup snapshot."""
    format_version: str
    created_at: str
    app_version: str
    databases: dict[str, DatabaseBackupMeta]
    record_counts: dict[str, int]
    note: str


def _sqlite_path_from_url(url: str) -> Path:
    """Extract local Path from a SQLAlchemy sqlite URL."""
    if not url.startswith("sqlite"):
        raise ValueError(f"Only SQLite URLs are supported for SQLite backup, got: {url}")
    parsed = urlparse(url)
    path_str = parsed.path
    if not path_str:
        # Handles sqlite:///./filename or sqlite:///:memory:
        path_str = url.replace("sqlite:///", "")
    if path_str.startswith("/") and len(path_str) > 2 and path_str[2] == ":":
        # Windows drive letter fix
        path_str = path_str[1:]
    return Path(path_str).resolve()


def _compute_sha256(filepath: Path) -> str:
    """Compute cryptographic SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def _verify_sqlite_integrity(db_path: Path) -> bool:
    """Verify physical SQLite database file integrity via PRAGMA integrity_check."""
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        res = cursor.fetchall()
        return len(res) == 1 and res[0][0] == "ok"
    finally:
        conn.close()


def _get_schema_version(db_path: Path) -> str | None:
    """Read alembic revision from alembic_version table if present."""
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version';"
        )
        if not cursor.fetchone():
            return None
        cursor.execute("SELECT version_num FROM alembic_version LIMIT 1;")
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception:  # noqa: BLE001
        return None
    finally:
        conn.close()


def create_backup(
    backup_dir: Path | str,
    db_session: Session | None = None,
    business_db_url: str | None = None,
    checkpoint_db_url: str | None = None,
    note: str = "Automated quiescent backup",
) -> BackupManifest:
    """Create a point-in-time, WAL-safe backup of Evidra SQLite databases.

    Uses the SQLite Online Backup API (sqlite3.Connection.backup) which safely flushes
    active WAL pages and copies consistent database pages without holding exclusive locks
    or stopping readers.
    """
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)

    b_url = business_db_url or settings.database_url
    c_url = checkpoint_db_url or settings.checkpoint_database_url

    primary_src = _sqlite_path_from_url(b_url)
    checkpoint_src = _sqlite_path_from_url(c_url)

    databases_meta: dict[str, DatabaseBackupMeta] = {}

    # 1. Backup primary business database
    if not primary_src.exists():
        raise FileNotFoundError(f"Primary database file does not exist at: {primary_src}")

    dest_primary = backup_path / "review.sqlite"
    src_conn = sqlite3.connect(str(primary_src))
    dest_conn = sqlite3.connect(str(dest_primary))
    try:
        with dest_conn:
            src_conn.backup(dest_conn)
    finally:
        src_conn.close()
        dest_conn.close()

    primary_ok = _verify_sqlite_integrity(dest_primary)
    primary_sha = _compute_sha256(dest_primary)
    primary_schema = _get_schema_version(dest_primary)
    primary_size = dest_primary.stat().st_size

    databases_meta["primary"] = DatabaseBackupMeta(
        name="primary_business_db",
        target_filename="review.sqlite",
        sha256=primary_sha,
        byte_size=primary_size,
        schema_version=primary_schema,
        integrity_ok=primary_ok,
    )

    # 2. Backup checkpoint database (if it exists)
    if checkpoint_src.exists():
        dest_checkpoint = backup_path / "checkpoints.sqlite"
        c_src_conn = sqlite3.connect(str(checkpoint_src))
        c_dest_conn = sqlite3.connect(str(dest_checkpoint))
        try:
            with c_dest_conn:
                c_src_conn.backup(c_dest_conn)
        finally:
            c_src_conn.close()
            c_dest_conn.close()

        cp_ok = _verify_sqlite_integrity(dest_checkpoint)
        cp_sha = _compute_sha256(dest_checkpoint)
        cp_size = dest_checkpoint.stat().st_size
        databases_meta["checkpoint"] = DatabaseBackupMeta(
            name="langgraph_checkpoint_db",
            target_filename="checkpoints.sqlite",
            sha256=cp_sha,
            byte_size=cp_size,
            schema_version=None,
            integrity_ok=cp_ok,
        )

    # 3. Gather domain record counts from session if available
    record_counts: dict[str, int] = {}
    if db_session:
        try:
            for table in [
                "workspaces",
                "corpus_revisions",
                "paper_groups",
                "review_events",
                "record_revisions",
            ]:
                count = db_session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0
                record_counts[table] = int(count)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Failed to query some record counts for backup manifest: {exc}")

    manifest = BackupManifest(
        format_version=BACKUP_FORMAT_VERSION,
        created_at=datetime.now(UTC).isoformat(),
        app_version=settings.app_version,
        databases=databases_meta,
        record_counts=record_counts,
        note=note,
    )

    # Serialize manifest
    manifest_dict = {
        "format_version": manifest.format_version,
        "created_at": manifest.created_at,
        "app_version": manifest.app_version,
        "databases": {k: asdict(v) for k, v in manifest.databases.items()},
        "record_counts": manifest.record_counts,
        "note": manifest.note,
    }
    manifest_file = backup_path / BACKUP_MANIFEST_NAME
    manifest_file.write_text(json.dumps(manifest_dict, indent=2), encoding="utf-8")

    return manifest


def restore_backup(
    backup_dir: Path | str,
    target_dir: Path | str,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Restore Evidra SQLite databases from a verified quiescent backup to target_dir.

    Verifies checksums and SQLite integrity before finalizing restoration.
    Fails safely if destination contains existing database files without overwrite=True.
    """
    src_dir = Path(backup_dir)
    dest_dir = Path(target_dir)

    manifest_file = src_dir / BACKUP_MANIFEST_NAME
    if not manifest_file.exists():
        raise FileNotFoundError(f"Missing backup manifest: {manifest_file}")

    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    dest_dir.mkdir(parents=True, exist_ok=True)

    restored_files: list[str] = []

    for db_meta in manifest_data.get("databases", {}).values():
        fname = db_meta["target_filename"]
        source_file = src_dir / fname
        target_file = dest_dir / fname

        if not source_file.exists():
            raise FileNotFoundError(f"Backup file referenced in manifest is missing: {source_file}")

        # Check sha256 of backup file
        actual_sha = _compute_sha256(source_file)
        if actual_sha != db_meta["sha256"]:
            raise ValueError(
                f"Backup file {fname} SHA256 mismatch: expected {db_meta['sha256']}, got {actual_sha}"
            )

        if target_file.exists() and not overwrite:
            raise FileExistsError(
                f"Target file already exists: {target_file}. Use overwrite=True to replace."
            )

        # Copy to destination
        shutil.copy2(source_file, target_file)

        # Verify integrity on target
        if not _verify_sqlite_integrity(target_file):
            target_file.unlink(missing_ok=True)
            raise RuntimeError(f"Restored database {target_file} failed SQLite integrity check")

        restored_files.append(str(target_file))

    return {
        "status": "success",
        "created_at": manifest_data.get("created_at"),
        "app_version": manifest_data.get("app_version"),
        "restored_files": restored_files,
        "record_counts": manifest_data.get("record_counts", {}),
    }
