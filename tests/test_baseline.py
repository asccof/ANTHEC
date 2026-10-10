import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('baseline_validator', ROOT / 'tools/validate_baseline.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'requirements/baseline.json').read_text())
        self.sources = json.loads((ROOT / 'requirements/sources.json').read_text())

    def test_current_baseline(self):
        self.assertEqual(MODULE.validate(self.data, self.sources), [])

    def test_missing_acceptance_detected(self):
        self.data['requirements'].pop(0)
        self.assertIn('Missing executive acceptance coverage', MODULE.validate(self.data, self.sources))

    def test_no_unproven_acceptance(self):
        self.data['requirements'][0]['status'] = 'verified'
        self.assertIn('Verified claim without evidence', MODULE.validate(self.data, self.sources))

    def test_unknown_source(self):
        self.data['requirements'][0]['source_id'] = 'invented'
        self.assertIn('Unknown source reference', MODULE.validate(self.data, self.sources))

    def test_scope_expansion_detected(self):
        for key in self.data['boundaries']:
            changed = copy.deepcopy(self.data)
            changed['boundaries'][key] = True
            self.assertIn('Authorization boundary changed', MODULE.validate(changed, self.sources))

    def test_duplicate_requirement(self):
        self.data['requirements'].append(copy.deepcopy(self.data['requirements'][0]))
        self.assertIn('Duplicate requirement ID', MODULE.validate(self.data, self.sources))


if __name__ == '__main__':
    unittest.main()
