import unittest

from experiments.freshness.cache_gateway import CacheGateway
from experiments.freshness.catalog_workload import CatalogWorkload
from experiments.freshness.dashboard_workload import DashboardWorkload
from experiments.freshness.dependencies import dashboard_query_affects, realworld_feed_affects
from experiments.freshness.realworld_workload import RealWorldFeedWorkload
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
            if policy in {
                'always-invalidate', 'always-update', 'write-reactive',
                'event-invalidate-with-repair',
            }:
                self.assertEqual(result.delivered_notification_ids, ('u1:0',))
                self.assertEqual(result.duplicate_notification_ids, ('u1:1',))
            else:
                self.assertEqual(result.delivered_notification_ids, ())
                self.assertEqual(result.duplicate_notification_ids, ())
            self.assertEqual(len(result.observations), 3)
            self.assertEqual(len(result.publication_records), 1)
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

    def test_w2_query_complete_update_is_snapshotted_at_commit(self):
        workload_id = 'svelte-realworld-feed-v1'
        query = '/api/articles?limit=10&offset=0'
        schedule = TraceSchedule(
            trace_id='w2-query-update-v1',
            seed=0,
            transport_mode='redis-pubsub',
            events=(
                TraceEvent('r0', 0, 'request', workload_id, query, {'decision_revision': 0}),
                TraceEvent('u1', 10, 'update', workload_id, 'independent-note-29', {
                    'expected_revision': 1,
                    'mutation': {
                        'operation': 'update',
                        'slug': 'independent-note-29',
                        'changes': {'title': 'Commit revision title'},
                    },
                }),
                TraceEvent('r1', 15, 'request', workload_id, query, {'decision_revision': 1}),
                TraceEvent('r2', 31, 'request', workload_id, query, {'decision_revision': 1}),
            ),
            faults=(FaultDirective('u1', delay_ms=20),),
        )
        workload = RealWorldFeedWorkload(article_count=30)
        self.addCleanup(workload.close)
        gateway = CacheGateway(
            workload, 'always-update', affects=realworld_feed_affects,
        )
        result = run_trace(schedule, gateway)
        self.assertFalse(result.observations[1].semantically_fresh)
        self.assertTrue(result.observations[2].semantically_fresh)
        self.assertTrue(result.observations[2].cache_hit)
        publication = result.publication_records[0]
        self.assertEqual(publication['query_update_count'], 1)
        self.assertEqual(publication['publisher_origin_reads'], 1)
        self.assertGreater(publication['notification_body_bytes'], 0)

    def test_w3_query_complete_update_refreshes_cached_resource(self):
        workload_id = 'react-admin-dashboard-v1'
        query = '/api/orders?sort=["id","ASC"]&range=[0,9]'
        schedule = TraceSchedule(
            trace_id='w3-query-update-v1',
            seed=0,
            transport_mode='redis-streams',
            events=(
                TraceEvent('r0', 0, 'request', workload_id, query, {'decision_revision': 0}),
                TraceEvent('u1', 10, 'update', workload_id, 'orders:1', {
                    'expected_revision': 1,
                    'mutation': {
                        'resource': 'orders',
                        'operation': 'update',
                        'id': 1,
                        'changes': {'total': 999},
                    },
                }),
                TraceEvent('r1', 11, 'request', workload_id, query, {'decision_revision': 1}),
            ),
        )
        workload = DashboardWorkload()
        gateway = CacheGateway(
            workload, 'always-update', affects=dashboard_query_affects,
        )
        result = run_trace(schedule, gateway)
        self.assertTrue(result.observations[1].semantically_fresh)
        self.assertTrue(result.observations[1].cache_hit)
        self.assertEqual(result.observations[1].content['records'][0]['total'], 999)
        self.assertEqual(result.publication_records[0]['query_update_count'], 1)

    def test_reordered_query_updates_cannot_replace_newer_revision(self):
        workload_id = 'svelte-realworld-feed-v1'
        query = '/api/articles?limit=10&offset=0'
        schedule = TraceSchedule(
            trace_id='w2-reordered-query-updates-v1',
            seed=0,
            transport_mode='redis-pubsub',
            events=(
                TraceEvent('r0', 0, 'request', workload_id, query, {'decision_revision': 0}),
                TraceEvent('u1', 10, 'update', workload_id, 'independent-note-29', {
                    'expected_revision': 1,
                    'mutation': {
                        'operation': 'update', 'slug': 'independent-note-29',
                        'changes': {'title': 'Older delayed title'},
                    },
                }),
                TraceEvent('u2', 20, 'update', workload_id, 'independent-note-29', {
                    'expected_revision': 2,
                    'mutation': {
                        'operation': 'update', 'slug': 'independent-note-29',
                        'changes': {'title': 'Newer delivered title'},
                    },
                }),
                TraceEvent('r1', 25, 'request', workload_id, query, {'decision_revision': 2}),
                TraceEvent('r2', 45, 'request', workload_id, query, {'decision_revision': 2}),
            ),
            faults=(FaultDirective('u1', delay_ms=30),),
        )
        workload = RealWorldFeedWorkload(article_count=30)
        self.addCleanup(workload.close)
        gateway = CacheGateway(
            workload, 'always-update', affects=realworld_feed_affects,
        )
        result = run_trace(schedule, gateway)
        self.assertTrue(result.observations[1].semantically_fresh)
        self.assertTrue(result.observations[2].semantically_fresh)
        self.assertEqual(
            result.observations[2].content['articles'][0]['title'],
            'Newer delivered title',
        )


if __name__ == '__main__':
    unittest.main()
