"""Run baseline or application checks under explicit stage control."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
from validate_stage import validate

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / '.ci-results'


def run(args, cwd, env):
    print('+ ' + ' '.join(args), flush=True)
    subprocess.run(args, cwd=cwd, env=env, check=True)


def main():
    state = validate()
    RESULTS.mkdir(exist_ok=True)
    mode = sys.argv[1]
    backend = ROOT / ('backend' if state['backend'] == 'application' else 'planning/dependencies/backend')
    frontend = ROOT / ('frontend' if state['frontend'] == 'application' else 'planning/dependencies/frontend')
    env = {**os.environ, 'CI': 'true', 'APP_ENV': 'test', 'AUTH_MODE': 'local', 'CI_OFFLINE': '1',
           'SOURCE_MODE': 'fixture', 'LLM_ENABLED': 'false', 'RAG_ENABLED': 'false', 'LANGSMITH_TRACING': 'false'}
    with tempfile.TemporaryDirectory(prefix='mini-rayyan-ci-') as data:
        env.update(DATA_DIR=data, DATABASE_URL=f'sqlite:///{data}/review.sqlite',
                   CHECKPOINT_DATABASE=f'{data}/checkpoints.sqlite')
        if mode == 'backend':
            py_bin = backend / ('.venv/Scripts/python.exe' if os.name == 'nt' else '.venv/bin/python')
            run(['uv', 'pip', 'check', '--python', str(py_bin)], ROOT, env)
            run(['uv', 'run', '--locked', 'python', 'dependency_smoke.py'], backend, env)
            if state['backend'] == 'application':
                run(['uv', 'run', '--locked', 'ruff', 'check', 'app', 'tests', 'scripts'], backend, env)
                heads = subprocess.check_output(['uv', 'run', '--locked', 'alembic', 'heads'], cwd=backend, env=env, text=True)
                if len([line for line in heads.splitlines() if line.strip()]) != 1:
                    raise RuntimeError('Exactly one Alembic head is required')
                run(['uv', 'run', '--locked', 'alembic', 'upgrade', 'head'], backend, env)
                run(['uv', 'run', '--locked', 'python', 'scripts/export_openapi.py', '--check'], backend, env)
                run(['uv', 'run', '--locked', 'pytest', '-q', f'--junitxml={RESULTS / "backend.xml"}'], backend, env)
        elif mode == 'frontend':
            run(['npm', 'ls', '--all'], frontend, env)
            run(['npm', 'run', 'check:dependencies'], frontend, env)
            if state['frontend'] == 'application':
                for command in ('api:check', 'typecheck', 'test:unit', 'build'):
                    run(['npm', 'run', command], frontend, env)
        elif mode == 'e2e':
            if not state['integration']:
                raise RuntimeError('e2e must not be invoked before integration activation')
            run(['npm', 'run', 'build'], frontend, env)

            import time
            import urllib.request

            serve_cmd = ['uv', 'run', '--locked', 'python', 'app/testing/serve.py']
            server_env = {**env, 'APP_ENV': 'test', 'SOURCE_MODE': 'fixture'}
            print('+ ' + ' '.join(serve_cmd) + ' (background)', flush=True)
            server_proc = subprocess.Popen(serve_cmd, cwd=backend, env=server_env)
            try:
                ready = False
                for _ in range(60):
                    try:
                        with urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=1) as resp:
                            if resp.status == 200:
                                ready = True
                                break
                    except Exception:
                        time.sleep(0.5)

                if not ready:
                    raise RuntimeError('Test server failed to respond on 127.0.0.1:8000/health/ready')

                e2e_env = {**env, 'CI_INTEGRATION': 'true', 'PLAYWRIGHT_BASE_URL': 'http://127.0.0.1:4173'}
                run(['npm', 'run', 'test:e2e'], frontend, e2e_env)
            finally:
                server_proc.terminate()
                try:
                    server_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server_proc.kill()
                    server_proc.wait()
        else:
            raise ValueError(f'Unsupported check group: {mode}')


if __name__ == '__main__':
    main()
