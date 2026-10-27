"""Validate explicit CI promotion state; missing app files never silently skip tests."""
from pathlib import Path
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def validate(root=ROOT):
    state = json.loads((root / '.ci/stages.json').read_text())
    if set(state) != {'backend', 'frontend', 'integration', 'level2', 'ai'}:
        raise ValueError('Unexpected/missing CI stage keys')
    for side in ('backend', 'frontend'):
        if state[side] not in ('planning', 'application'):
            raise ValueError(f'Invalid {side} stage')
    for flag in ('integration', 'level2', 'ai'):
        if type(state[flag]) is not bool:
            raise ValueError(f'{flag} must be Boolean')
    for side, manifest, lock in [('backend', 'pyproject.toml', 'uv.lock'), ('frontend', 'package.json', 'package-lock.json')]:
        active = root / (side if state[side] == 'application' else f'planning/dependencies/{side}')
        if not all((active / f).is_file() for f in (manifest, lock)):
            raise ValueError(f'Missing {side} manifest/lock at {active}')
        inactive = root / (f'planning/dependencies/{side}' if state[side] == 'application' else side)
        if any((inactive / f).exists() for f in (manifest, lock)):
            raise ValueError(f'Two active {side} manifests or an unannounced promotion')
    required = []
    if state['backend'] == 'application':
        required += ['backend/app/main.py', 'backend/alembic.ini', 'backend/scripts/export_openapi.py',
                     'backend/dependency_smoke.py', 'backend/tests/contracts/test_contracts.py', 'contracts/openapi.json']
    if state['frontend'] == 'application':
        required += ['frontend/index.html', 'frontend/src/main.tsx', 'frontend/src/api/schema.d.ts']
        package = json.loads((root / 'frontend/package.json').read_text())
        for command in ('typecheck', 'test:unit', 'build', 'api:check', 'check:dependencies'):
            if command not in package.get('scripts', {}):
                raise ValueError(f'Missing frontend script: {command}')
    if state['integration']:
        if state['backend'] != 'application' or state['frontend'] != 'application':
            raise ValueError('Integration requires both applications')
        required += ['backend/app/testing/serve.py', 'frontend/playwright.config.ts',
                     'frontend/tests/e2e/level1.spec.ts']
        package = json.loads((root / 'frontend/package.json').read_text())
        if 'test:e2e' not in package.get('scripts', {}):
            raise ValueError('Missing frontend test:e2e script')
    for flag in ('level2', 'ai'):
        if state[flag] and not state['integration']:
            raise ValueError(f'{flag} requires integration')
    if state['level2']:
        required += ['backend/tests/level2/test_snapshot_restore.py',
                     'frontend/tests/e2e/level2/restore.spec.ts']
    if state['ai']:
        required += ['backend/tests/ai/test_assistant_boundaries.py']
    for path in required:
        if not (root / path).is_file():
            raise ValueError(f'Promoted stage requires {path}')
    return state


def no_downgrade(state, base):
    # Compare trusted checkout objects, not interpolated branch names or shell code.
    if not base:
        return
    if not all(c in '0123456789abcdef' for c in base) or len(base) != 40:
        raise ValueError('Expected a 40-character base commit')
    result = subprocess.run(['git', 'show', f'{base}:.ci/stages.json'], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        # A first PR adding this pipeline may have no stage file on its base.
        exists = subprocess.run(['git', 'cat-file', '-e', f'{base}^{{commit}}'], cwd=ROOT, capture_output=True)
        if exists.returncode:
            raise ValueError('Cannot inspect CI base commit')
        return
    previous = json.loads(result.stdout)
    for side in ('backend', 'frontend'):
        if previous.get(side) == 'application' and state[side] != 'application':
            raise ValueError(f'CI {side} stage cannot be downgraded')
    for flag in ('integration', 'level2', 'ai'):
        if previous.get(flag) is True and state[flag] is not True:
            raise ValueError(f'CI {flag} coverage cannot be disabled')


if __name__ == '__main__':
    state = validate()
    no_downgrade(state, os.environ.get('CI_BASE_SHA', ''))
    outputs = {**state,
               'backend_root': 'backend' if state['backend'] == 'application' else 'planning/dependencies/backend',
               'frontend_root': 'frontend' if state['frontend'] == 'application' else 'planning/dependencies/frontend'}
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            for key, value in outputs.items():
                stream.write(f'{key}={str(value).lower() if isinstance(value, bool) else value}\n')
    print(json.dumps(outputs, indent=2))
