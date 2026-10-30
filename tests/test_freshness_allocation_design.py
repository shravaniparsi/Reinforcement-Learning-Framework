import unittest
from pathlib import Path

from experiments.freshness.allocation_design import AllocationDesign


DESIGN_PATH = Path('experiments/freshness/allocation_design_v1.json')


class FreshnessAllocationDesignTests(unittest.TestCase):
    def setUp(self):
        self.design = AllocationDesign.load(DESIGN_PATH)
        self.identity = {
            'stage': 'engineering',
            'workload': 'mutable-product-v1',
            'regime': 'balanced',
            'trace_seed': 0,
            'transport': 'redis-pubsub',
            'fault_profile': 'no-fault',
        }

    def test_all_policies_share_one_allocation_block(self):
        self.assertEqual(len(self.design.policies_per_allocation), 8)
        self.assertEqual(self.design.application_failure_retries, 0)
        self.assertTrue(self.design.retain_all_attempts)

    def test_policy_order_is_deterministic_and_identity_bound(self):
        first = self.design.policy_order(self.identity)
        second = self.design.policy_order(dict(self.identity))
        changed = self.design.policy_order({**self.identity, 'trace_seed': 1})
        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)
        self.assertEqual(set(first), set(self.design.policies_per_allocation))

    def test_incomplete_block_identity_fails(self):
        incomplete = dict(self.identity)
        del incomplete['fault_profile']
        with self.assertRaisesRegex(ValueError, 'does not match'):
            self.design.policy_order(incomplete)


if __name__ == '__main__':
    unittest.main()
