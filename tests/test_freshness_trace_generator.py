import unittest
from pathlib import Path

from experiments.freshness.cache_gateway import CacheGateway
from experiments.freshness.catalog_workload import CatalogWorkload
from experiments.freshness.dashboard_workload import DashboardWorkload
from experiments.freshness.fault_schedule import materialize_notifications
from experiments.freshness.realworld_workload import RealWorldFeedWorkload
from experiments.freshness.trace_generator import TraceDesign, generate_schedule
from experiments.freshness.trace_runner import run_trace


DESIGN_PATH = Path('experiments/freshness/trace_design_v1.json')


class FreshnessTraceGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design = TraceDesign.load(DESIGN_PATH)

    def schedule(self, workload, profile='no-fault', regime='balanced', seed=0):
        return generate_schedule(
            self.design,
            workload_id=workload,
            regime=regime,
            partition='engineering',
            seed=seed,
            fault_profile=profile,
            transport_mode='redis-pubsub',
        )

    def test_design_has_disjoint_partitions_and_stable_digest(self):
        reloaded = TraceDesign.load(DESIGN_PATH)
        self.assertEqual(reloaded.digest(), self.design.digest())
        seeds = []
        for partition in self.design.partitions.values():
            values = set(range(
                partition['seed_start'], partition['seed_start'] + partition['seed_count'],
            ))
            self.assertFalse(any(values & previous for previous in seeds))
            seeds.append(values)

    def test_trace_counts_first_request_and_determinism(self):
        schedule = self.schedule('mutable-product-v1', regime='read-heavy')
        replay = self.schedule('mutable-product-v1', regime='read-heavy')
        requests = [event for event in schedule.events if event.kind == 'request']
        updates = [event for event in schedule.events if event.kind == 'update']
        self.assertEqual(len(requests), 500)
        self.assertEqual(len(updates), 100)
        self.assertEqual(schedule.events[0].kind, 'request')
        self.assertEqual(schedule.digest(), replay.digest())

    def test_fault_profiles_preserve_trace_identity_and_exact_counts(self):
        workload = 'svelte-realworld-feed-v1'
        base = self.schedule(workload)
        loss = self.schedule(workload, 'loss-5pct')
        duplicate = self.schedule(workload, 'duplicate-5pct')
        reorder = self.schedule(workload, 'reorder-5pct')
        self.assertEqual(base.trace_digest(), loss.trace_digest())
        self.assertEqual(base.trace_digest(), duplicate.trace_digest())
        self.assertEqual(base.trace_digest(), reorder.trace_digest())
        self.assertNotEqual(base.fault_digest(), loss.fault_digest())

        delivered, dropped = materialize_notifications(loss)
        self.assertEqual(len(dropped), 5)
        self.assertEqual(len(delivered), 95)
        delivered, dropped = materialize_notifications(duplicate)
        self.assertEqual(len(dropped), 0)
        self.assertEqual(len(delivered), 105)
        delivered, _ = materialize_notifications(reorder)
        source_sequences = [item.source_sequence for item in delivered]
        inversions = sum(
            current < previous
            for previous, current in zip(source_sequences, source_sequences[1:])
        )
        self.assertGreaterEqual(inversions, 5)

    def test_combined_profile_never_duplicates_a_dropped_update(self):
        schedule = self.schedule('react-admin-dashboard-v1', 'combined-stress')
        by_id = {fault.update_event_id: fault for fault in schedule.faults}
        dropped = {key for key, fault in by_id.items() if fault.drop}
        duplicated = {key for key, fault in by_id.items() if fault.duplicate_delays_ms}
        self.assertEqual(len(dropped), 5)
        self.assertEqual(len(duplicated), 5)
        self.assertFalse(dropped & duplicated)

    def test_partition_rejects_seed_outside_declared_range(self):
        with self.assertRaisesRegex(ValueError, 'outside'):
            generate_schedule(
                self.design,
                workload_id='mutable-product-v1',
                regime='balanced',
                partition='final-test',
                seed=0,
                fault_profile='no-fault',
                transport_mode='redis-pubsub',
            )

    def test_each_workload_schedule_executes_against_origin_contract(self):
        cases = (
            ('mutable-product-v1', CatalogWorkload(product_count=20)),
            ('svelte-realworld-feed-v1', RealWorldFeedWorkload(article_count=30)),
            ('react-admin-dashboard-v1', DashboardWorkload()),
        )
        for workload_id, workload in cases:
            with self.subTest(workload=workload_id):
                try:
                    result = run_trace(
                        self.schedule(workload_id),
                        CacheGateway(workload, 'bypass'),
                    )
                    self.assertEqual(len(result.committed_event_ids), 100)
                    self.assertEqual(len(result.observations), 200)
                    self.assertTrue(all(item.semantically_fresh for item in result.observations))
                finally:
                    workload.close()


if __name__ == '__main__':
    unittest.main()
