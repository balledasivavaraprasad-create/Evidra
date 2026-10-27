"""Export deterministic OpenAPI specification to repository root contracts/openapi.json."""
import argparse
import json
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parents[1]
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.main import app

REPO_ROOT = backend_root.parent
TARGET_FILE = REPO_ROOT / "contracts" / "openapi.json"


def generate_openapi_json() -> str:
    """Generate normalized, deterministically formatted OpenAPI JSON string."""
    spec = app.openapi()
    # Sort keys for deterministic output across runs and environments
    return json.dumps(spec, indent=2, sort_keys=True) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export or verify OpenAPI schema")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify committed contracts/openapi.json matches app schema without modifying it",
    )
    args = parser.parse_args()

    content = generate_openapi_json()

    if args.check:
        if not TARGET_FILE.exists():
            print(f"Error: Target file {TARGET_FILE} does not exist.", file=sys.stderr)
            sys.exit(1)

        existing_content = TARGET_FILE.read_text(encoding="utf-8")
        if existing_content != content:
            print(
                "Error: Committed contracts/openapi.json has drifted from FastAPI application schema.\n"
                "Run `python backend/scripts/export_openapi.py` to regenerate.",
                file=sys.stderr,
            )
            sys.exit(1)
        print("OpenAPI schema check passed: contracts/openapi.json is strictly up to date.")
    else:
        TARGET_FILE.parent.mkdir(parents=True, exist_ok=True)
        TARGET_FILE.write_text(content, encoding="utf-8")
        print(f"Successfully exported OpenAPI schema to {TARGET_FILE}")


if __name__ == "__main__":
    main()
