"""Unit and integration tests for SQLite WAL-safe backup and restore operations (D06)."""
import sqlite3
from pathlib import Path

import pytest

from app.services.backup import (
    BACKUP_MANIFEST_NAME,
    create_backup,
    restore_backup,
)


@pytest.fixture
def sample_databases(tmp_path: Path):
    """Create a pair of source business and checkpoint SQLite databases with WAL mode."""
    biz_path = tmp_path / "source_review.sqlite"
    cp_path = tmp_path / "source_checkpoints.sqlite"

    # Initialize business db with table and records
    conn1 = sqlite3.connect(str(biz_path))
    conn1.execute("PRAGMA journal_mode=WAL;")
    conn1.execute("CREATE TABLE workspaces (id TEXT PRIMARY KEY, title TEXT);")
    conn1.execute("CREATE TABLE alembic_version (version_num TEXT);")
    conn1.execute("INSERT INTO alembic_version VALUES ('d06_head');")
    conn1.execute("INSERT INTO workspaces VALUES ('ws-1', 'Review A');")
    conn1.execute("INSERT INTO workspaces VALUES ('ws-2', 'Review B');")
    conn1.commit()
    conn1.close()

    # Initialize checkpoint db
    conn2 = sqlite3.connect(str(cp_path))
    conn2.execute("PRAGMA journal_mode=WAL;")
    conn2.execute("CREATE TABLE checkpoints (thread_id TEXT PRIMARY KEY, state TEXT);")
    conn2.execute("INSERT INTO checkpoints VALUES ('th-1', '{\"step\": 2}');")
    conn2.commit()
    conn2.close()

    return biz_path, cp_path


def test_backup_creates_valid_snapshot_and_manifest(tmp_path: Path, sample_databases):
    biz_path, cp_path = sample_databases
    backup_dir = tmp_path / "backup_dest"

    manifest = create_backup(
        backup_dir=backup_dir,
        business_db_url=f"sqlite:///{biz_path}",
        checkpoint_db_url=f"sqlite:///{cp_path}",
        note="Test backup",
    )

    assert (backup_dir / BACKUP_MANIFEST_NAME).exists()
    assert (backup_dir / "review.sqlite").exists()
    assert (backup_dir / "checkpoints.sqlite").exists()

    assert manifest.format_version == "1.0.0"
    assert "primary" in manifest.databases
    assert "checkpoint" in manifest.databases
    assert manifest.databases["primary"].schema_version == "d06_head"
    assert manifest.databases["primary"].integrity_ok is True
    assert manifest.databases["checkpoint"].integrity_ok is True


def test_restore_to_fresh_directory(tmp_path: Path, sample_databases):
    biz_path, cp_path = sample_databases
    backup_dir = tmp_path / "backup_dest"
    restore_dir = tmp_path / "restored_dir"

    create_backup(
        backup_dir=backup_dir,
        business_db_url=f"sqlite:///{biz_path}",
        checkpoint_db_url=f"sqlite:///{cp_path}",
    )

    result = restore_backup(backup_dir=backup_dir, target_dir=restore_dir)
    assert result["status"] == "success"
    assert len(result["restored_files"]) == 2

    # Query restored databases
    restored_biz = restore_dir / "review.sqlite"
    conn = sqlite3.connect(str(restored_biz))
    rows = conn.execute("SELECT id, title FROM workspaces ORDER BY id;").fetchall()
    conn.close()

    assert len(rows) == 2
    assert rows[0] == ("ws-1", "Review A")
    assert rows[1] == ("ws-2", "Review B")

    restored_cp = restore_dir / "checkpoints.sqlite"
    cp_conn = sqlite3.connect(str(restored_cp))
    cp_rows = cp_conn.execute("SELECT thread_id, state FROM checkpoints;").fetchall()
    cp_conn.close()

    assert len(cp_rows) == 1
    assert cp_rows[0][0] == "th-1"


def test_restore_fails_on_tampered_backup(tmp_path: Path, sample_databases):
    biz_path, cp_path = sample_databases
    backup_dir = tmp_path / "backup_dest"
    restore_dir = tmp_path / "restored_tampered"

    create_backup(
        backup_dir=backup_dir,
        business_db_url=f"sqlite:///{biz_path}",
        checkpoint_db_url=f"sqlite:///{cp_path}",
    )

    # Tamper with backup file
    dest_file = backup_dir / "review.sqlite"
    with open(dest_file, "ab") as f:
        f.write(b"tamper_bytes_corruption")

    with pytest.raises(ValueError, match="SHA256 mismatch"):
        restore_backup(backup_dir=backup_dir, target_dir=restore_dir)


def test_restore_safe_conflict_handling(tmp_path: Path, sample_databases):
    biz_path, cp_path = sample_databases
    backup_dir = tmp_path / "backup_dest"
    restore_dir = tmp_path / "restored_conflict"
    restore_dir.mkdir(parents=True, exist_ok=True)

    create_backup(
        backup_dir=backup_dir,
        business_db_url=f"sqlite:///{biz_path}",
        checkpoint_db_url=f"sqlite:///{cp_path}",
    )

    # Pre-create conflicting destination file
    (restore_dir / "review.sqlite").write_text("existing content")

    # Fails by default without overwrite=True
    with pytest.raises(FileExistsError, match="Target file already exists"):
        restore_backup(backup_dir=backup_dir, target_dir=restore_dir, overwrite=False)

    # Succeeds with overwrite=True
    res = restore_backup(backup_dir=backup_dir, target_dir=restore_dir, overwrite=True)
    assert res["status"] == "success"
