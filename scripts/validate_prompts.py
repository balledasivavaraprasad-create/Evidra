"""Check prompt dependency DAG, canonical order and explicit handoff metadata."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def validate_tasks(data, root=ROOT):
    tasks = data['tasks']
    ids = {t['id'] for t in tasks}
    if len(ids) != len(tasks):
        raise ValueError('Duplicate prompt IDs')
    if sorted(t['merge_order'] for t in tasks) != list(range(1, len(tasks) + 1)):
        raise ValueError('Merge positions must be unique and consecutive')
    by_id = {t['id']: t for t in tasks}
    for t in tasks:
        if not re.fullmatch(r'[ABCD]\d{2}', t['id']):
            raise ValueError('Invalid prompt ID')
        if t['developer'] != 'dev-' + t['id'][0]:
            raise ValueError('Developer mismatch')
        if t['scope'] not in ('required', 'bonus', 'optional'):
            raise ValueError('Invalid scope')
        if not t['file'].startswith(f'prompts/{t["developer"]}/'):
            raise ValueError('Prompt folder mismatch')
        path = root / t['file']
        if not path.is_file():
            raise ValueError(f'Missing prompt {t["file"]}')
        content = path.read_text()
        for heading in ('## Prerequisites', '## Ownership', '## Implementation', '## Verification', '## Handoff'):
            if heading not in content:
                raise ValueError(f'{t["id"]} missing {heading}')
        for dep in t['depends_on']:
            if dep not in ids or by_id[dep]['merge_order'] >= t['merge_order']:
                raise ValueError(f'Invalid/cyclic/out-of-order dependency: {t["id"]} -> {dep}')
            if dep not in content:
                raise ValueError(f'{t["id"]} omits prerequisite {dep}')
        if t['branch'] not in content:
            raise ValueError(f'{t["id"]} omits branch')
    # A required path must never depend on an optional branch.
    for t in tasks:
        if t['scope'] == 'required':
            pending = list(t['depends_on'])
            seen = set()
            while pending:
                dep = pending.pop()
                if dep in seen:
                    continue
                seen.add(dep)
                if by_id[dep]['scope'] != 'required':
                    raise ValueError(f'Required prompt {t["id"]} depends on optional {dep}')
                pending.extend(by_id[dep]['depends_on'])
    return {'prompts': len(tasks), 'developers': sorted({t['developer'] for t in tasks}),
            'required': sum(t['scope'] == 'required' for t in tasks),
            'bonus': sum(t['scope'] == 'bonus' for t in tasks),
            'optional': sum(t['scope'] == 'optional' for t in tasks), 'dag': 'acyclic'}


if __name__ == '__main__':
    print(json.dumps(validate_tasks(json.loads((ROOT / 'prompts/tasks.json').read_text())), indent=2))
