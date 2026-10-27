"""Download one pinned actionlint binary and verify its committed SHA-256."""
from pathlib import Path
import hashlib
import io
import json
import os
import platform
import sys
import tarfile
import urllib.request

root = Path(__file__).resolve().parents[2]
config = json.loads((root / '.ci/actionlint.json').read_text())
machine = {'x86_64': 'amd64', 'aarch64': 'arm64'}.get(platform.machine(), platform.machine())
key = platform.system().lower() + '_' + machine
entry = config['platforms'][key]
with urllib.request.urlopen(entry['url'], timeout=60) as response:
    archive = response.read()
if hashlib.sha256(archive).hexdigest() != entry['sha256']:
    raise SystemExit('actionlint checksum mismatch')
destination = Path(sys.argv[1]).resolve()
destination.mkdir(parents=True, exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tar:
    # Extract only expected executable bytes; never extract paths from an archive.
    member = tar.getmember('actionlint')
    if not member.isfile():
        raise SystemExit('Expected a regular executable')
    source = tar.extractfile(member)
    if source is None:
        raise SystemExit('Missing executable')
    binary = destination / 'actionlint'
    binary.write_bytes(source.read())
binary.chmod(0o755)
print(binary)
if os.environ.get('GITHUB_PATH'):
    with open(os.environ['GITHUB_PATH'], 'a') as output:
        output.write(str(destination) + '\n')
