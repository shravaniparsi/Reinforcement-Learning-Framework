import tempfile
import unittest
from pathlib import Path

from experiments.freshness.analyze_final_test import _estimate, analyze


class FreshnessFinalAnalysisTests(unittest.TestCase):
    def test_estimate_uses_67_complete_pairs_and_no_p_value(self):
        treatment = {seed: float(seed % 3) for seed in range(67)}
        reference = {seed: 1.0 for seed in range(67)}
        estimate = _estimate(
            treatment,
            reference,
            {'contrast_id': 'fixture', 'outcome_id': 'fixture'},
        )
        self.assertEqual(estimate['n'], 67)
        self.assertEqual(estimate['resamples'], 10_000)
        self.assertEqual(estimate['confidence'], 0.99)
        self.assertNotIn('p_value', estimate)

    def test_incomplete_campaign_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, '4824 blocks'):
                analyze(Path(directory))


if __name__ == '__main__':
    unittest.main()
