import json
import tempfile
import unittest
from pathlib import Path

from experiments.freshness.analyze_final_test import _estimate, _json_normalize, analyze
from experiments.freshness.trace_generator import TraceDesign, generate_schedule


class FreshnessFinalAnalysisTests(unittest.TestCase):
    def test_persisted_schedule_matches_json_normalized_generator(self):
        design = TraceDesign.load(Path('experiments/freshness/trace_design_v2.json'))
        schedule = generate_schedule(
            design,
            workload_id='mutable-product-v1',
            regime='balanced',
            partition='final-test',
            seed=1000,
            fault_profile='loss-10pct',
            transport_mode='redis-pubsub',
        )
        persisted = json.loads(json.dumps(schedule.to_mapping(), allow_nan=False))
        self.assertNotEqual(persisted, schedule.to_mapping())
        self.assertEqual(persisted, _json_normalize(schedule.to_mapping()))
        self.assertEqual(
            persisted['faults'][0]['duplicate_delays_ms'],
            [],
        )

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
