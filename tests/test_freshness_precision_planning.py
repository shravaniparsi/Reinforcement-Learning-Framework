import tempfile
import unittest
from pathlib import Path

from experiments.freshness.plan_final_sample_size import (
    _outcome_value, _precision_calculation, plan,
)


class FreshnessPrecisionPlanningTests(unittest.TestCase):
    def test_relative_target_uses_reference_mean_and_paired_trace_units(self):
        result = _precision_calculation(
            [11.0, 13.0, 15.0],
            [10.0, 10.0, 10.0],
            {'target_kind': 'reference_fraction', 'target_value': 0.10},
        )
        self.assertEqual(result['planning_trace_units'], 3)
        self.assertEqual(result['reference_mean'], 10.0)
        self.assertEqual(result['target_half_width'], 1.0)
        self.assertGreaterEqual(result['required_final_seeds'], 8)

    def test_total_origin_bytes_include_request_and_publisher_work(self):
        summary = {
            'origin_response_body_bytes': 125,
            'publisher_origin_response_body_bytes': 75,
        }
        self.assertEqual(_outcome_value(summary, 'total_origin_response_body_bytes'), 200)

    def test_incomplete_campaign_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, '720 complete blocks'):
                plan(Path(directory))


if __name__ == '__main__':
    unittest.main()
