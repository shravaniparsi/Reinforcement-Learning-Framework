import unittest
from pathlib import Path

from experiments.freshness.locked_execution import (
    load_event_lock, load_locked_costs, load_time_lock, locked_unit_specs,
)


class FreshnessLockedExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.costs = load_locked_costs(Path(
            'data/training/freshness-costs-40982405656/locked_costs.json'
        ))
        cls.time = load_time_lock(Path(
            'data/training/freshness-time-candidates-40984591923/'
            'selected_time_parameters.json'
        ))
        cls.event = load_event_lock(Path(
            'data/training/freshness-event-candidates-41006126071-archives/'
            'selected_event_parameters.json'
        ))

    def test_all_eight_policies_use_locked_options(self):
        specs = locked_unit_specs(
            self.costs, self.time, self.event, 'mutable-product-v1', 'read-heavy',
        )
        self.assertEqual(len(specs), 8)
        by_policy = {item.policy: item for item in specs}
        self.assertEqual(set(by_policy), {
            'bypass', 'conditional-validation', 'fixed-ttl',
            'stale-while-revalidate', 'always-invalidate', 'always-update',
            'write-reactive', 'event-invalidate-with-repair',
        })
        self.assertEqual(by_policy['fixed-ttl'].options, {'ttl_ms': 25})
        self.assertEqual(
            by_policy['stale-while-revalidate'].options,
            {'ttl_ms': 25, 'stale_window_ms': 10},
        )
        self.assertEqual(
            by_policy['event-invalidate-with-repair'].options,
            {'repair_ms': 50},
        )
        self.assertEqual(by_policy['write-reactive'].options['initial_expected_writes'], 0.25)
        self.assertEqual(by_policy['write-reactive'].options['update_cost'], 367.0)


if __name__ == '__main__':
    unittest.main()
