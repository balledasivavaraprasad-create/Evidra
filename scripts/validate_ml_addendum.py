"""Validate the additive dev-C scope without mutating the original task plan."""
from pathlib import Path
import copy
import json

ROOT = Path(__file__).resolve().parents[1]
SUPPLEMENT = ROOT / 'prompts/dev-C/ml-supplement.tasks.json'


def validate_addendum(base, extra, root=ROOT):
    if extra['schema_version'] != 1 or extra['base_files_modified'] is not False:
        raise ValueError('The ML supplement must be additive schema version 1')
    original = {task['id']: copy.deepcopy(task) for task in base['tasks']}
    excluded = set(extra['unselected_original_tasks'])
    if excluded != {'B05'} or not excluded <= original.keys():
        raise ValueError('Only the duplicate original B05 ML experiment is unselected')
    tasks = {key: task for key, task in original.items() if key not in excluded}
    if extra['scope_overrides'] != {'C05': 'required', 'C06': 'required'}:
        raise ValueError('The existing LLM/RAG path must be required')
    for key, scope in extra['scope_overrides'].items():
        tasks[key]['scope'] = scope
    if len(extra['tasks']) != 3:
        raise ValueError('Exactly three supplemental ML prompts are expected')
    for task in extra['tasks']:
        if task['id'] in original or task['id'] in tasks:
            raise ValueError('Duplicate supplemental task ID')
        if task['developer'] != 'dev-C' or task['scope'] != 'required':
            raise ValueError('All supplemental ML implementation belongs to dev-C and is required')
        path = root / task['file']
        if not task['file'].startswith('prompts/dev-C/') or not path.is_file():
            raise ValueError('Missing or misplaced supplemental prompt')
        content = path.read_text()
        for expected in [task['id'], task['branch'], '**Priority:** required',
                         'ML-ADDENDUM-EXECUTION.md', *task['depends_on']]:
            if expected not in content:
                raise ValueError(f"{task['id']} prompt omits {expected}")
        tasks[task['id']] = copy.deepcopy(task)
    if set(task['id'] for task in extra['tasks']) != {'C-ML01', 'C-ML02', 'C-ML03'}:
        raise ValueError('Unexpected supplemental task names')
    for key, dependencies in extra['additional_dependencies'].items():
        if key not in tasks:
            raise ValueError('Unknown task in additional dependencies')
        tasks[key]['depends_on'] = list(dict.fromkeys(tasks[key]['depends_on'] + dependencies))
    order = extra['example_merge_order']
    if len(order) != len(tasks) or set(order) != set(tasks):
        raise ValueError('Example order must contain every selected task exactly once')
    positions = {key: index for index, key in enumerate(order)}
    # Preserve the relative order of all selected original assignments.
    original_order = [t['id'] for t in sorted(base['tasks'], key=lambda t: t['merge_order'])
                      if t['id'] not in excluded]
    if [key for key in order if key in original] != original_order:
        raise ValueError('Original relative merge order changed')
    for key, task in tasks.items():
        for dep in task['depends_on']:
            if dep not in tasks or positions[dep] >= positions[key]:
                raise ValueError(f'Unknown, cyclic or out-of-order dependency: {key} -> {dep}')
    def ancestors(key):
        seen = set()
        pending = list(tasks[key]['depends_on'])
        while pending:
            dep = pending.pop()
            if dep not in seen:
                seen.add(dep)
                pending.extend(tasks[dep]['depends_on'])
        return seen
    for key, task in tasks.items():
        if task['scope'] == 'required' and any(tasks[d]['scope'] != 'required' for d in ancestors(key)):
            raise ValueError(f'Required task {key} depends on bonus/unselected work')
    mandatory = {'C-ML01', 'C-ML02', 'C-ML03', 'C05', 'C06'}
    for release_task in ('B06', 'A06'):
        if not mandatory <= ancestors(release_task):
            raise ValueError(f'{release_task} can bypass required ML/RAG acceptance')
    if not mandatory <= set(extra['release_requires']):
        raise ValueError('Release requirements omit required ML/RAG work')
    return {'supplemental_prompts': 3, 'ml_owner': 'dev-C',
            'selected_total_tasks': len(tasks),
            'required_tasks': sum(t['scope'] == 'required' for t in tasks.values()),
            'bonus_tasks': sum(t['scope'] == 'bonus' for t in tasks.values()),
            'original_relative_order': 'preserved', 'graph': 'acyclic',
            'release_requires_ml_and_rag': True,
            'scope': 'Plan consistency only; no feature implementation or merge proof'}


if __name__ == '__main__':
    extra = json.loads(SUPPLEMENT.read_text())
    base = json.loads((ROOT / extra['base_manifest']).read_text())
    print(json.dumps(validate_addendum(base, extra), indent=2))
