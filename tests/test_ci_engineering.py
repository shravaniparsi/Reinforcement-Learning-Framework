"""Fail-closed checks for the separate CI engineering path; no browser required."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ci_engineering', ROOT/'experiments/ci_engineering/run.py')
ci = importlib.util.module_from_spec(spec); spec.loader.exec_module(ci)
from main_study_design import session_schedule


class EngineeringGates(unittest.TestCase):
    def setUp(self):
        self.schedule = session_schedule('engineering', 0)
        self.rows = [{**t, 'status': 'ok', 'correctness': True,
                      'metrics': {'mount_hydration_ms': 10},
                      'content_sha256': t['pair_id'], 'errors': [], 'external_requests': []}
                     for t in self.schedule['trials']]

    def test_complete_matrix(self):
        ci.validate(self.rows, self.schedule, [True] * 24)

    def test_rejects_incomplete_error_nonlocal_and_content_mismatch(self):
        invalid = []
        invalid.append(self.rows[:-1])
        for field, value in [('errors', ['request failed']), ('external_requests', ['https://example.org']),
                             ('content_sha256', 'different-content'), ('correctness', False)]:
            rows = copy.deepcopy(self.rows); rows[0][field] = value; invalid.append(rows)
        for rows in invalid:
            with self.subTest(rows=rows[0]), self.assertRaises(ValueError):
                ci.validate(rows, self.schedule, [True])

    def test_adapter_checks_required(self):
        for checks in [[], [False], [True, False]]:
            with self.subTest(checks=checks), self.assertRaises(ValueError):
                ci.validate(self.rows, self.schedule, checks)

    def test_refuses_local_or_self_hosted_build(self):
        with patch.dict('os.environ', {}, clear=True), self.assertRaises(RuntimeError):
            ci.fresh_runner_only()
        with patch.dict('os.environ', {'GITHUB_ACTIONS': 'true', 'RUNNER_ENVIRONMENT': 'self-hosted'}, clear=True), \
                patch('platform.system', return_value='Linux'), self.assertRaises(RuntimeError):
            ci.fresh_runner_only()


if __name__ == '__main__':
    unittest.main()
