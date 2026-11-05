import unittest
from pathlib import Path

from experiments.freshness.clustered_loss_design import (
    ClusteredLossDesign, generate_clustered_schedule, loss_indices,
)
from experiments.freshness.fault_schedule import materialize_notifications
from experiments.freshness.trace_generator import TraceDesign


PACKAGE = Path('experiments/freshness')


class ClusteredLossDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = TraceDesign.load(PACKAGE / 'trace_design_v2.json')
        cls.design = ClusteredLossDesign.load(
            PACKAGE / 'clustered_loss_design_v1.json', cls.base,
        )

    def schedule(self, profile, seed=2000):
        return generate_clustered_schedule(
            self.design, self.base,
            workload_id='mutable-product-v1', regime='balanced',
            partition='extension-engineering', seed=seed,
            fault_profile=profile, transport_mode='redis-pubsub',
        )

    def test_extension_seeds_do_not_overlap_original_partitions(self):
        original = set()
        for item in self.base.partitions.values():
            original.update(range(item['seed_start'], item['seed_start'] + item['seed_count']))
        extension = set()
        for item in self.design.source['partitions'].values():
            extension.update(range(item['seed_start'], item['seed_start'] + item['seed_count']))
        self.assertFalse(original & extension)

    def test_profiles_match_loss_count_and_protect_trace_ends(self):
        for profile in ('dispersed-10', 'single-burst-10', 'repeated-bursts-10'):
            with self.subTest(profile=profile):
                indices = loss_indices(self.design, profile, 2000)
                self.assertEqual(len(indices), 10)
                self.assertEqual(len(set(indices)), 10)
                self.assertGreaterEqual(min(indices), 20)
                self.assertLess(max(indices), 80)
                delivered, dropped = materialize_notifications(self.schedule(profile))
                self.assertEqual(len(dropped), 10)
                self.assertEqual(len(delivered), 90)

    def test_temporal_shapes_are_enforced(self):
        dispersed = loss_indices(self.design, 'dispersed-10', 2000)
        single = loss_indices(self.design, 'single-burst-10', 2000)
        repeated = loss_indices(self.design, 'repeated-bursts-10', 2000)
        self.assertTrue(all(right - left > 1 for left, right in zip(dispersed, dispersed[1:])))
        self.assertEqual(single, tuple(range(single[0], single[0] + 10)))
        self.assertEqual(repeated[:5], tuple(range(repeated[0], repeated[0] + 5)))
        self.assertEqual(repeated[5:], tuple(range(repeated[5], repeated[5] + 5)))
        self.assertGreaterEqual(repeated[5] - repeated[4], 6)

    def test_profiles_share_the_same_exogenous_trace(self):
        schedules = [self.schedule(profile) for profile in self.design.source['fault_profiles']]
        self.assertEqual(len({item.trace_digest() for item in schedules}), 1)
        self.assertEqual(len({item.fault_digest() for item in schedules}), 4)

    def test_generation_is_deterministic_and_rejects_final_stage(self):
        first = self.schedule('single-burst-10')
        second = self.schedule('single-burst-10')
        self.assertEqual(first.digest(), second.digest())
        with self.assertRaisesRegex(ValueError, 'outside'):
            generate_clustered_schedule(
                self.design, self.base,
                workload_id='mutable-product-v1', regime='balanced',
                partition='final-test', seed=3000,
                fault_profile='single-burst-10', transport_mode='redis-pubsub',
            )


if __name__ == '__main__':
    unittest.main()
