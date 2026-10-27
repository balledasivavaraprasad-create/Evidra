"""The existing CI unittest discovery picks up these supplemental-plan checks."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_ml_addendum import validate_addendum


class MLAddendumTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads((ROOT / 'prompts/tasks.json').read_text())
        self.extra = json.loads((ROOT / 'prompts/dev-C/ml-supplement.tasks.json').read_text())

    def test_three_c_owned_tasks_preserve_original_order(self):
        result = validate_addendum(self.base, self.extra)
        self.assertEqual(result['supplemental_prompts'], 3)
        self.assertEqual(result['ml_owner'], 'dev-C')
        self.assertEqual(result['required_tasks'], 22)
        self.assertEqual(result['bonus_tasks'], 4)

    def test_no_new_ml_implementation_can_be_assigned_to_another_owner(self):
        self.extra['tasks'][1]['developer'] = 'dev-A'
        with self.assertRaisesRegex(ValueError, 'belongs to dev-C'):
            validate_addendum(self.base, self.extra)

    def test_release_cannot_skip_final_ml_acceptance(self):
        self.extra['additional_dependencies']['B06'] = []
        with self.assertRaisesRegex(ValueError, 'B06 can bypass'):
            validate_addendum(self.base, self.extra)

    def test_rag_cannot_revert_to_optional(self):
        self.extra['scope_overrides']['C06'] = 'optional'
        with self.assertRaisesRegex(ValueError, 'RAG path must be required'):
            validate_addendum(self.base, self.extra)

    def test_original_merge_order_cannot_be_rewritten(self):
        order = self.extra['example_merge_order']
        order[1], order[2] = order[2], order[1]
        with self.assertRaisesRegex(ValueError, 'relative merge order changed'):
            validate_addendum(self.base, self.extra)

    def test_late_ml_completion_cannot_follow_final_release(self):
        order = self.extra['example_merge_order']
        order.remove('C-ML03')
        order.append('C-ML03')
        with self.assertRaisesRegex(ValueError, 'out-of-order dependency'):
            validate_addendum(self.base, self.extra)

    def test_existing_manifest_is_not_mutated(self):
        before = json.dumps(self.base, sort_keys=True)
        validate_addendum(self.base, self.extra)
        self.assertEqual(before, json.dumps(self.base, sort_keys=True))


if __name__ == '__main__':
    unittest.main()
