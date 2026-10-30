import tempfile
import unittest
from pathlib import Path

from experiments.freshness.validate_locked_parameters import _confirmation, validate


class FreshnessValidationAnalysisTests(unittest.TestCase):
    def test_confirmation_uses_frozen_one_point_margin(self):
        passing = _confirmation(0.02, [0.025, 0.035], 0.01)
        failing = _confirmation(0.02, [0.031, 0.031], 0.01)
        self.assertTrue(passing['passed'])
        self.assertFalse(failing['passed'])
        self.assertEqual(passing['trace_units'], 2)

    def test_incomplete_campaign_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, '1080 complete blocks'):
                validate(Path(directory))


if __name__ == '__main__':
    unittest.main()
