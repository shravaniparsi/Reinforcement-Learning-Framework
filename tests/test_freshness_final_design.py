import unittest
import json
from pathlib import Path

from experiments.freshness.allocation_design import AllocationDesign
from experiments.freshness.final_design import FinalDesign, load_sample_size_lock
from experiments.freshness.trace_generator import TraceDesign


class FreshnessFinalDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = Path('experiments/freshness')
        cls.trace = TraceDesign.load(package / 'trace_design_v2.json')
        cls.allocation = AllocationDesign.load(package / 'allocation_design_v1.json')
        cls.sample_lock = load_sample_size_lock(Path(
            'data/variance/freshness-variance-41131844320-archives/'
            'final_sample_size_lock.json'
        ))
        cls.design = FinalDesign.load(
            package / 'final_design_v1.json', cls.trace, cls.allocation, cls.sample_lock,
        )

    def test_expansion_matches_locked_requirement(self):
        self.assertEqual(self.sample_lock['required_final_seeds'], 67)
        self.assertEqual(self.design.seed_start, 1000)
        self.assertEqual(self.design.seed_count, 67)
        self.assertEqual(self.design.expected_blocks, 4824)
        self.assertEqual(self.design.expected_full_trace_units, 38592)
        self.assertEqual(self.design.expected_primary_estimates, 450)

    def test_v2_changes_only_design_identity_and_final_seed_count(self):
        package = Path('experiments/freshness')
        historical = json.loads((package / 'trace_design_v1.json').read_text())
        expanded = json.loads((package / 'trace_design_v2.json').read_text())
        self.assertEqual(historical['design_id'], 'freshness-bounded-synthetic-v1')
        self.assertEqual(expanded['design_id'], 'freshness-bounded-synthetic-v2')
        historical['design_id'] = expanded['design_id']
        historical['partitions']['final-test']['seed_count'] = 67
        self.assertEqual(historical, expanded)

    def test_only_primary_conditions_are_confirmatory(self):
        self.assertEqual(
            self.design.fault_profiles,
            ('no-fault', 'loss-1pct', 'loss-5pct', 'loss-10pct'),
        )
        identity = {
            'stage': 'final-test', 'workload': 'mutable-product-v1',
            'regime': 'balanced', 'trace_seed': 1066,
            'transport': 'redis-streams', 'fault_profile': 'loss-10pct',
        }
        self.assertTrue(self.design.contains(identity))
        self.assertFalse(self.design.contains({**identity, 'trace_seed': 1067}))
        self.assertFalse(self.design.contains({**identity, 'fault_profile': 'delay-10ms'}))


if __name__ == '__main__':
    unittest.main()
