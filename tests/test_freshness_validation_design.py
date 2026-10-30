import unittest
from pathlib import Path

from experiments.freshness.allocation_design import AllocationDesign
from experiments.freshness.trace_generator import TraceDesign
from experiments.freshness.validation_design import ValidationDesign


class FreshnessValidationDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = Path('experiments/freshness')
        cls.trace = TraceDesign.load(package / 'trace_design_v1.json')
        cls.allocation = AllocationDesign.load(package / 'allocation_design_v1.json')
        cls.design = ValidationDesign.load(
            package / 'validation_design_v1.json', cls.trace, cls.allocation,
        )

    def test_full_held_out_campaign_is_frozen(self):
        self.assertEqual(self.design.seed_start, 200)
        self.assertEqual(self.design.seed_count, 5)
        self.assertEqual(self.design.expected_blocks, 1080)
        self.assertEqual(self.design.expected_full_trace_units, 8640)
        self.assertEqual(len(self.design.fault_profiles), 12)

    def test_identity_must_be_inside_validation_partition(self):
        identity = {
            'stage': 'validation', 'workload': 'mutable-product-v1',
            'regime': 'balanced', 'trace_seed': 200,
            'transport': 'redis-pubsub', 'fault_profile': 'no-fault',
        }
        self.assertTrue(self.design.contains(identity))
        self.assertFalse(self.design.contains({**identity, 'trace_seed': 100}))
        self.assertFalse(self.design.contains({**identity, 'stage': 'final-test'}))


if __name__ == '__main__':
    unittest.main()
