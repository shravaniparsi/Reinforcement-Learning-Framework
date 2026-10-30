import unittest
from pathlib import Path

from experiments.freshness.training_campaign import TrainingCampaign
from experiments.freshness.training_execution import (
    load_locked_costs, load_time_lock, unit_specs,
)
from experiments.freshness.run_candidate_block import _ordered_specs
from experiments.freshness.allocation_design import AllocationDesign


class FreshnessTrainingExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.campaign = TrainingCampaign.load(
            Path('experiments/freshness/training_campaign_v1.json'),
            Path('experiments/freshness/parameter_grid_v1.json'),
            Path('experiments/freshness/trace_design_v1.json'),
        )
        cls.costs = load_locked_costs(
            Path('data/training/freshness-costs-40982405656/locked_costs.json'),
        )
        cls.time_lock = load_time_lock(Path(
            'data/training/freshness-time-candidates-40984591923/'
            'selected_time_parameters.json'
        ))

    def test_time_phase_has_all_families_and_48_units(self):
        specs = unit_specs(
            self.campaign, self.costs, 'time-candidates',
            'mutable-product-v1', 'balanced',
        )
        self.assertEqual(len(specs), 48)
        self.assertEqual(len({item.unit_id for item in specs}), 48)
        self.assertEqual(len({item.policy for item in specs}), 8)
        self.assertEqual(sum(item.candidate for item in specs), 42)

    def test_event_phase_has_all_families_and_locked_costs(self):
        specs = unit_specs(
            self.campaign, self.costs, 'event-candidates',
            'svelte-realworld-feed-v1', 'read-heavy',
            time_lock=self.time_lock,
        )
        self.assertEqual(len(specs), 18)
        self.assertEqual(len({item.policy for item in specs}), 8)
        self.assertEqual(sum(item.candidate for item in specs), 12)
        reactive = [item for item in specs if item.policy == 'write-reactive']
        self.assertEqual(len(reactive), 6)
        self.assertTrue(all(item.options['update_cost'] == 17468.0 for item in reactive))
        self.assertTrue(all(item.options['invalidate_cost'] == 196.0 for item in reactive))
        self.assertTrue(all(item.options['miss_cost'] == 5342.0 for item in reactive))
        controls = {item.policy: item for item in specs if not item.candidate}
        self.assertEqual(controls['fixed-ttl'].options, {'ttl_ms': 10})
        self.assertEqual(
            controls['stale-while-revalidate'].options,
            {'ttl_ms': 10, 'stale_window_ms': 10},
        )

    def test_unit_order_is_deterministic_and_identity_bound(self):
        specs = unit_specs(
            self.campaign, self.costs, 'time-candidates',
            'mutable-product-v1', 'balanced',
        )
        allocation = AllocationDesign.load(
            Path('experiments/freshness/allocation_design_v1.json'),
        )
        identity = {
            'stage': 'training', 'workload': 'mutable-product-v1',
            'regime': 'balanced', 'trace_seed': 100,
            'transport': 'redis-pubsub', 'fault_profile': 'no-fault',
        }
        first = _ordered_specs(allocation, identity, 'time-candidates', specs)
        second = _ordered_specs(allocation, dict(identity), 'time-candidates', specs)
        changed = _ordered_specs(
            allocation, {**identity, 'trace_seed': 101}, 'time-candidates', specs,
        )
        self.assertEqual(first, second)
        self.assertNotEqual(
            [item.unit_id for item in first], [item.unit_id for item in changed],
        )


if __name__ == '__main__':
    unittest.main()
