import unittest
from pathlib import Path

from experiments.freshness.allocation_design import AllocationDesign
from experiments.freshness.trace_generator import TraceDesign
from experiments.freshness.variance_design import VarianceDesign, load_passed_validation


class FreshnessVarianceDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = Path('experiments/freshness')
        cls.trace = TraceDesign.load(package / 'trace_design_v1.json')
        cls.allocation = AllocationDesign.load(package / 'allocation_design_v1.json')
        cls.design = VarianceDesign.load(
            package / 'variance_design_v1.json', cls.trace, cls.allocation,
        )

    def test_primary_precision_campaign_is_frozen(self):
        self.assertEqual(self.design.seed_start, 300)
        self.assertEqual(self.design.seed_count, 10)
        self.assertEqual(self.design.expected_blocks, 720)
        self.assertEqual(self.design.expected_full_trace_units, 5760)
        self.assertEqual(self.design.expected_precision_calculations, 450)

    def test_identity_must_be_inside_variance_partition(self):
        identity = {
            'stage': 'variance-planning', 'workload': 'mutable-product-v1',
            'regime': 'balanced', 'trace_seed': 300,
            'transport': 'redis-pubsub', 'fault_profile': 'loss-1pct',
        }
        self.assertTrue(self.design.contains(identity))
        self.assertFalse(self.design.contains({**identity, 'trace_seed': 200}))
        self.assertFalse(self.design.contains({**identity, 'fault_profile': 'delay-10ms'}))

    def test_passed_validation_is_a_required_prerequisite(self):
        report = load_passed_validation(Path(
            'data/validation/freshness-validation-41099780817-archives/'
            'validation_report.json'
        ))
        self.assertTrue(report['passed'])
        self.assertFalse(report['allow_refitting'])


if __name__ == '__main__':
    unittest.main()
