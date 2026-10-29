import unittest

from experiments.freshness.cache_gateway import CacheGateway
from experiments.freshness.catalog_workload import CatalogWorkload
from experiments.freshness.schema import FaultDirective, TraceEvent, TraceSchedule
from experiments.freshness.trace_runner import run_trace


class FreshnessTraceRunnerTests(unittest.TestCase):
    def schedule(self):
        workload = 'mutable-product-v1'
        return TraceSchedule(
            trace_id='w1-engineering-replay-v1',
            seed=7,
            transport_mode='redis-pubsub',
            events=(
                TraceEvent('r0', 0, 'request', workload, 'product-1', {'decision_revision': 0}),
                TraceEvent('u1', 10, 'update', workload, 'product-1', {
                    'expected_revision': 1,
                    'mutation': {'key': 'product-1', 'changes': {'price_cents': 5000}},
                }),
                TraceEvent('r1', 20, 'request', workload, 'product-1', {'decision_revision': 1}),
                TraceEvent('r2', 60, 'request', workload, 'product-1', {'decision_revision': 1}),
            ),
            faults=(FaultDirective('u1', delay_ms=30, duplicate_delays_ms=(35,)),),
        )

    def gateway(self, workload, policy):
        options = {
            'fixed-ttl': {'ttl_ms': 25},
            'stale-while-revalidate': {'ttl_ms': 25, 'stale_window_ms': 50},
            'event-invalidate-with-repair': {'repair_ms': 25},
            'write-reactive': {
                'update_cost': 1,
                'invalidate_cost': 1,
                'miss_cost': 4,
                'initial_expected_writes': 1,
            },
        }.get(policy, {})
        return CacheGateway(workload, policy, **options)

    def test_same_trace_runs_through_every_supported_w1_policy(self):
        schedule = self.schedule()
        policies = (
            'bypass',
            'conditional-validation',
            'fixed-ttl',
            'stale-while-revalidate',
            'always-invalidate',
            'always-update',
            'write-reactive',
            'event-invalidate-with-repair',
        )
        identities = set()
        for policy in policies:
            workload = CatalogWorkload(product_count=4)
            self.addCleanup(workload.close)
            result = run_trace(schedule, self.gateway(workload, policy))
            identities.add((result.trace_sha256, result.fault_sha256))
            self.assertEqual(result.committed_event_ids, ('u1',))
            self.assertEqual(result.delivered_notification_ids, ('u1:0',))
            self.assertEqual(result.duplicate_notification_ids, ('u1:1',))
            self.assertEqual(len(result.observations), 3)
        self.assertEqual(len(identities), 1)

    def test_replay_resets_origin_and_gateway_state(self):
        workload = CatalogWorkload(product_count=4)
        self.addCleanup(workload.close)
        gateway = self.gateway(workload, 'always-update')
        first = run_trace(self.schedule(), gateway)
        second = run_trace(self.schedule(), gateway)
        self.assertEqual(first.to_mapping(), second.to_mapping())

    def test_dropped_notification_remains_visible(self):
        schedule = self.schedule()
        dropped = TraceSchedule(
            trace_id=schedule.trace_id,
            seed=schedule.seed,
            transport_mode=schedule.transport_mode,
            events=schedule.events,
            faults=(FaultDirective('u1', drop=True),),
        )
        workload = CatalogWorkload(product_count=4)
        self.addCleanup(workload.close)
        result = run_trace(dropped, self.gateway(workload, 'always-invalidate'))
        self.assertEqual(result.delivered_notification_ids, ())
        self.assertEqual(result.dropped_notification_ids, ('u1:0',))
        self.assertFalse(result.observations[1].semantically_fresh)


if __name__ == '__main__':
    unittest.main()
