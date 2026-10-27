"""Validate planning-package links and manifest consistency without network access."""
from pathlib import Path
import json
import re
import tomllib

ROOT = Path(__file__).resolve().parents[1]
errors = []
markdown = [ROOT / 'README.md', ROOT / 'AGENTS.md', ROOT / 'audit.md']
markdown += list((ROOT / 'docs').glob('*.md'))
markdown += list((ROOT / 'skills').glob('*/SKILL.md'))
markdown += list((ROOT / 'prompts').rglob('*.md'))
for path in markdown:
    if not path.exists():
        errors.append(f'Missing required file: {path.relative_to(ROOT)}')
        continue
    content = path.read_text()
    for target in re.findall(r'\]\(([^)]+)\)', content):
        if target.startswith(('https://', 'http://', '#', 'mailto:')):
            continue
        target = target.split('#')[0].strip('<>')
        if not (path.parent / target).exists():
            errors.append(f'{path.relative_to(ROOT)}: broken link {target}')

stage = json.loads((ROOT / '.ci/stages.json').read_text())
backend = ROOT / ('backend' if stage['backend'] == 'application' else 'planning/dependencies/backend')
frontend = ROOT / ('frontend' if stage['frontend'] == 'application' else 'planning/dependencies/frontend')
pyproject = tomllib.loads((backend / 'pyproject.toml').read_text())
uvlock = tomllib.loads((backend / 'uv.lock').read_text())
locked_python = {p['name']: p['version'] for p in uvlock['package']}
requirements = pyproject['project']['dependencies'] + pyproject['dependency-groups']['dev']
for requirement in requirements:
    if '==' not in requirement:
        errors.append(f'Unpinned Python dependency: {requirement}')
        continue
    name, version = requirement.split('==')
    if locked_python.get(name) != version:
        errors.append(f'Python manifest/lock disagreement: {requirement}')

manifest = json.loads((frontend / 'package.json').read_text())
lock = json.loads((frontend / 'package-lock.json').read_text())
recorded = json.loads((ROOT / 'docs/validation/direct-dependencies.json').read_text())
for section, evidence_key in [('dependencies', 'frontend'), ('devDependencies', 'frontend_dev')]:
    if manifest[section] != lock['packages'][''][section]:
        errors.append(f'Frontend root manifest/lock disagreement in {section}')
    if manifest[section] != recorded[evidence_key]:
        errors.append(f'Frontend recorded metadata disagrees in {section}')
    for name, version in manifest[section].items():
        if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[\w.]+)?', version):
            errors.append(f'Unpinned npm dependency: {name} {version}')
        if lock['packages'].get('node_modules/' + name, {}).get('version') != version:
            errors.append(f'Frontend package resolution disagreement: {name}')

for path in (ROOT / 'skills').glob('*/SKILL.md'):
    content = path.read_text()
    if not content.startswith('---\n'):
        errors.append(f'Missing skill frontmatter: {path.parent.name}')
    if f'name: {path.parent.name}\n' not in content:
        errors.append(f'Skill name mismatch: {path.parent.name}')
    if 'description:' not in content.split('---', 2)[1]:
        errors.append(f'Missing skill description: {path.parent.name}')

report = {'checked_markdown_files': len(markdown), 'python_direct_pins': len(requirements),
          'frontend_direct_pins': len(manifest['dependencies']) + len(manifest['devDependencies']),
          'skills': len(list((ROOT / 'skills').glob('*/SKILL.md'))), 'errors': errors}
print(json.dumps(report, indent=2))
raise SystemExit(bool(errors))
