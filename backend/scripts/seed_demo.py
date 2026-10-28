"""Load the synthetic metformin demo review into the configured database, once.

Used by the container entrypoint when SEED_DEMO=true so a fresh hosted deployment
opens on a working review instead of empty pages. Safe to run on every start: it
does nothing if the demo workspace already exists, so reviewers' work is never
overwritten.
"""
from __future__ import annotations

import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parents[1]
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.db.models import WorkspaceModel
from app.db.session import SessionLocal
from app.demo_data import seed_synthetic_slr_workspace

DEMO_WORKSPACE_ID = "ws-synth-001"


def main() -> int:
    db = SessionLocal()
    try:
        if db.get(WorkspaceModel, DEMO_WORKSPACE_ID) is not None:
            print(f"Demo review '{DEMO_WORKSPACE_ID}' already present; leaving existing data untouched.")
            return 0
        seed_synthetic_slr_workspace(db)
        db.commit()
        print(f"Loaded demo review '{DEMO_WORKSPACE_ID}'.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
