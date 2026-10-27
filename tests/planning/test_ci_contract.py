"""Regression tests for CI gates and the developer dependency contract."""
import copy
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'scripts/ci'))
from check_gate import failures
from validate_prompts import validate_tasks
from validate_stage import no_downgrade, validate


class StageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = dict(backend='planning', frontend='planning',
                          integration=False, level2=False, ai=False)
        for side, names in [('backend', ('pyproject.toml', 'uv.lock')),
                            ('frontend', ('package.json', 'package-lock.json'))]:
            for name in names:
                self.put(f'planning/dependencies/{side}/{name}', '{}')
        self.save()

    def put(self, path, content=''):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def save(self):
        self.put('.ci/stages.json', json.dumps(self.state))

    def test_planning_stage_is_valid(self):
        self.assertEqual(validate(self.root), self.state)

    def test_missing_lock_fails(self):
        (self.root / 'planning/dependencies/backend/uv.lock').unlink()
        with self.assertRaisesRegex(ValueError, 'manifest/lock'):
            validate(self.root)

    def test_second_active_manifest_fails(self):
        self.put('backend/pyproject.toml')
        with self.assertRaisesRegex(ValueError, 'Two active'):
            validate(self.root)

    def test_string_false_is_not_boolean(self):
        self.state['integration'] = 'false'
        self.save()
        with self.assertRaisesRegex(ValueError, 'Boolean'):
            validate(self.root)

    def test_integration_cannot_skip_applications(self):
        self.state['integration'] = True
        self.save()
        with self.assertRaisesRegex(ValueError, 'both applications'):
            validate(self.root)

    def test_bonus_stage_requires_integration(self):
        for flag in ('level2', 'ai'):
            with self.subTest(flag=flag):
                self.state[flag] = True
                self.save()
                with self.assertRaisesRegex(ValueError, 'requires integration'):
                    validate(self.root)
                self.state[flag] = False

    def test_promoting_backend_requires_application_files(self):
        (self.root / 'planning/dependencies/backend').rename(self.root / 'backend')
        self.state['backend'] = 'application'
        self.save()
        with self.assertRaisesRegex(ValueError, 'backend/app/main.py'):
            validate(self.root)
        for name in ('backend/app/main.py', 'backend/alembic.ini',
                     'backend/scripts/export_openapi.py', 'backend/dependency_smoke.py',
                     'backend/tests/contracts/test_contracts.py', 'contracts/openapi.json'):
            self.put(name)
        self.assertEqual(validate(self.root)['backend'], 'application')

    def test_promoting_frontend_requires_test_scripts(self):
        (self.root / 'planning/dependencies/frontend').rename(self.root / 'frontend')
        self.state['frontend'] = 'application'
        self.save()
        with self.assertRaisesRegex(ValueError, 'Missing frontend script'):
            validate(self.root)

    def test_invalid_base_cannot_be_interpreted_as_shell(self):
        with patch('validate_stage.subprocess.run') as run:
            with self.assertRaisesRegex(ValueError, 'base commit'):
                no_downgrade(self.state, 'main; echo unsafe')
            run.assert_not_called()

    def test_pr_cannot_downgrade_activated_coverage(self):
        previous = {**self.state, 'backend': 'application', 'integration': True}
        result = subprocess.CompletedProcess([], 0, json.dumps(previous), '')
        with patch('validate_stage.subprocess.run', return_value=result):
            with self.assertRaisesRegex(ValueError, 'cannot be downgraded'):
                no_downgrade(self.state, 'a' * 40)

    def test_pr_cannot_disable_bonus_tests(self):
        previous = {**self.state, 'ai': True}
        result = subprocess.CompletedProcess([], 0, json.dumps(previous), '')
        with patch('validate_stage.subprocess.run', return_value=result):
            with self.assertRaisesRegex(ValueError, 'coverage cannot be disabled'):
                no_downgrade(self.state, 'a' * 40)

    def test_first_ci_pr_can_add_stage_file_to_real_base(self):
        results = [subprocess.CompletedProcess([], 128, '', 'missing path'),
                   subprocess.CompletedProcess([], 0, '', '')]
        with patch('validate_stage.subprocess.run', side_effect=results):
            no_downgrade(self.state, 'a' * 40)

    def test_missing_base_object_fails_closed(self):
        result = subprocess.CompletedProcess([], 128, '', 'unknown revision')
        with patch('validate_stage.subprocess.run', return_value=result):
            with self.assertRaisesRegex(ValueError, 'Cannot inspect'):
                no_downgrade(self.state, 'a' * 40)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.needs = {name: {'result': 'success'} for name in
                      ('validate', 'backend', 'frontend', 'security')}
        self.needs['validate']['outputs'] = {'integration': 'false'}
        self.needs['e2e'] = {'result': 'skipped'}

    def test_planning_may_skip_only_e2e(self):
        self.assertEqual(failures(self.needs), [])

    def test_required_failure_cancel_and_skip_each_fail_gate(self):
        for result in ('failure', 'cancelled', 'skipped'):
            with self.subTest(result=result):
                self.needs['backend']['result'] = result
                self.assertIn('backend', failures(self.needs))

    def test_missing_job_fails_gate(self):
        del self.needs['security']
        self.assertIn('security', failures(self.needs))

    def test_integrated_stage_requires_e2e_success(self):
        self.needs['validate']['outputs']['integration'] = 'true'
        self.assertEqual(failures(self.needs), ['e2e'])
        self.needs['e2e']['result'] = 'success'
        self.assertEqual(failures(self.needs), [])

    def test_unexpected_e2e_failure_is_not_hidden(self):
        self.needs['e2e']['result'] = 'failure'
        self.assertIn('e2e', failures(self.needs))


class PromptGraphTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'prompts/tasks.json').read_text())

    def test_current_package_has_six_prompts_per_developer(self):
        result = validate_tasks(self.data)
        self.assertEqual((result['prompts'], result['required'], result['bonus'], result['optional']),
                         (24, 17, 4, 3))
        for developer in result['developers']:
            self.assertEqual(sum(t['developer'] == developer for t in self.data['tasks']), 6)

    def test_duplicate_ids_fail(self):
        self.data['tasks'].append(copy.deepcopy(self.data['tasks'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate prompt IDs'):
            validate_tasks(self.data)

    def test_cycle_or_forward_dependency_fails(self):
        self.data['tasks'][0]['depends_on'] = [self.data['tasks'][-1]['id']]
        with self.assertRaisesRegex(ValueError, 'out-of-order dependency'):
            validate_tasks(self.data)

    def test_required_task_cannot_inherit_optional_work(self):
        self.data['tasks'][0]['scope'] = 'optional'
        with self.assertRaisesRegex(ValueError, 'depends on optional'):
            validate_tasks(self.data)

    def test_duplicate_merge_position_fails(self):
        self.data['tasks'][1]['merge_order'] = 1
        with self.assertRaisesRegex(ValueError, 'unique and consecutive'):
            validate_tasks(self.data)

    def test_workflow_action_refs_are_full_recorded_commit_pins(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        pins = json.loads((ROOT / 'docs/validation/github-action-pins.json').read_text())
        recorded = {f"{p['repository']}@{p['sha']}" for p in pins}
        refs = re.findall(r'uses: ([\w./-]+@\S+)', workflow)
        self.assertTrue(refs)
        for ref in refs:
            self.assertRegex(ref.split('@')[1], r'^[a-f0-9]{40}$')
            self.assertIn(ref, recorded)

    def test_master_queue_and_prompt_metadata_agree(self):
        order = (ROOT / 'prompts/EXECUTION-AND-MERGE-ORDER.md').read_text()
        queue = order.split('## Ready-to-start parallel waves', 1)[0]
        rows = [line for line in queue.splitlines() if re.match(r'^\| \d+ \|', line)]
        self.assertEqual(len(rows), len(self.data['tasks']))
        tasks = sorted(self.data['tasks'], key=lambda task: task['merge_order'])
        for row, task in zip(rows, tasks):
            columns = [part.strip() for part in row.split('|')[1:-1]]
            self.assertEqual(int(columns[0]), task['merge_order'])
            self.assertIn(f"{task['id']} — {task['developer']}", columns[1])
            self.assertIn(task['file'].removeprefix('prompts/'), columns[1])
            self.assertEqual(columns[3], ', '.join(task['depends_on']) or 'Bootstrap')
            self.assertEqual(columns[4], task['scope'])
            prompt = (ROOT / task['file']).read_text()
            self.assertIn(f"**Priority:** {task['scope']}", prompt)
            self.assertIn(f"**Canonical merge position:** {task['merge_order']} of 24", prompt)
            for path in task['allowed_paths']:
                self.assertIn(f'`{path}`', prompt)


if __name__ == '__main__':
    unittest.main()
