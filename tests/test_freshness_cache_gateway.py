import unittest

from experiments.freshness.cache_gateway import CacheGateway
from experiments.freshness.catalog_workload import CatalogWorkload
from experiments.freshness.dependencies import dashboard_query_affects, realworld_feed_affects


class CacheGatewayTests(unittest.TestCase):
    def setUp(self):
        self.workload = CatalogWorkload(product_count=4)

    def tearDown(self):
        self.workload.close()

    def update(self, price, at_ms=10):
        return self.workload.commit({
            'key': 'product-1', 'changes': {'price_cents': price},
        }, at_ms=at_ms)

    def test_bypass_and_conditional_validation_remain_fresh(self):
        bypass = CacheGateway(self.workload, 'bypass')
        first = bypass.read('product-1', at_ms=0, decision_revision=0)
        self.assertTrue(first.semantically_fresh)
        self.assertEqual(first.origin_operation, 'fetch')
        self.update(5000)
        second = bypass.read('product-1', at_ms=20, decision_revision=1)
        self.assertTrue(second.semantically_fresh)
        self.assertFalse(second.cache_hit)

        self.workload.reset(0)
        conditional = CacheGateway(self.workload, 'conditional-validation')
        conditional.read('product-1', 0, 0)
        unchanged = conditional.read('product-1', 5, 0)
        self.assertEqual(unchanged.origin_operation, 'validate')
        self.assertTrue(unchanged.cache_hit)
        self.update(6000)
        changed = conditional.read('product-1', 20, 1)
        self.assertTrue(changed.semantically_fresh)
        self.assertFalse(changed.cache_hit)

    def test_fixed_ttl_exposes_bounded_stale_interval(self):
        gateway = CacheGateway(self.workload, 'fixed-ttl', ttl_ms=100)
        gateway.read('product-1', 0, 0)
        self.update(5000)
        stale = gateway.read('product-1', 50, 1)
        self.assertFalse(stale.semantically_fresh)
        self.assertEqual(stale.revision_lag, 1)
        self.assertTrue(stale.cache_hit)
        refreshed = gateway.read('product-1', 100, 1)
        self.assertTrue(refreshed.semantically_fresh)
        self.assertEqual(refreshed.origin_operation, 'fetch')

    def test_stale_while_revalidate_serves_once_then_refreshes(self):
        gateway = CacheGateway(
            self.workload, 'stale-while-revalidate', ttl_ms=100, stale_window_ms=200,
        )
        gateway.read('product-1', 0, 0)
        self.update(5000)
        stale = gateway.read('product-1', 100, 1)
        self.assertFalse(stale.semantically_fresh)
        self.assertTrue(stale.cache_hit)
        self.assertEqual(stale.origin_operation, 'background-validate')
        fresh = gateway.read('product-1', 101, 1)
        self.assertTrue(fresh.semantically_fresh)
        self.assertTrue(fresh.cache_hit)

    def test_stale_while_revalidate_blocks_after_window(self):
        gateway = CacheGateway(
            self.workload, 'stale-while-revalidate', ttl_ms=100, stale_window_ms=200,
        )
        gateway.read('product-1', 0, 0)
        self.update(5000)
        refreshed = gateway.read('product-1', 300, 1)
        self.assertTrue(refreshed.semantically_fresh)
        self.assertEqual(refreshed.origin_operation, 'validate')

    def test_invalidation_depends_on_delivered_notification(self):
        gateway = CacheGateway(self.workload, 'always-invalidate')
        gateway.read('product-1', 0, 0)
        commit = self.update(5000)
        stale = gateway.read('product-1', 15, 1)
        self.assertFalse(stale.semantically_fresh)
        self.assertTrue(gateway.notify('u1:0', 'product-1', commit.notification_payload))
        self.assertFalse(gateway.notify('u1:0', 'product-1', commit.notification_payload))
        fresh = gateway.read('product-1', 20, 1)
        self.assertTrue(fresh.semantically_fresh)
        self.assertEqual(fresh.origin_operation, 'fetch')

    def test_repair_bounds_loss_without_delivery(self):
        gateway = CacheGateway(
            self.workload, 'event-invalidate-with-repair', repair_ms=100,
        )
        gateway.read('product-1', 0, 0)
        self.update(5000)
        self.assertFalse(gateway.read('product-1', 99, 1).semantically_fresh)
        repaired = gateway.read('product-1', 100, 1)
        self.assertTrue(repaired.semantically_fresh)
        self.assertEqual(repaired.origin_operation, 'validate')

    def test_always_update_applies_full_object_notification(self):
        gateway = CacheGateway(self.workload, 'always-update')
        gateway.read('product-1', 0, 0)
        commit = self.update(5000)
        gateway.notify(
            'u1:0', 'product-1', commit.notification_payload, at_ms=15,
        )
        fresh = gateway.read('product-1', 20, 1)
        self.assertTrue(fresh.semantically_fresh)
        self.assertTrue(fresh.cache_hit)
        self.assertEqual(gateway.state()['last_write_action']['product-1'], 'update')

    def test_always_update_ignores_older_revision(self):
        gateway = CacheGateway(self.workload, 'always-update')
        gateway.read('product-1', 0, 0)
        first = self.update(5000)
        gateway.notify('u1:0', 'product-1', first.notification_payload, at_ms=15)
        second = self.update(6000, at_ms=20)
        gateway.notify('u2:0', 'product-1', second.notification_payload, at_ms=25)
        gateway.notify('u1:1', 'product-1', first.notification_payload, at_ms=30)
        fresh = gateway.read('product-1', 35, 2)
        self.assertTrue(fresh.semantically_fresh)
        self.assertEqual(fresh.served_revision, 2)

    def test_rejected_update_notification_does_not_reserve_identity(self):
        gateway = CacheGateway(self.workload, 'always-update')
        gateway.read('product-1', 0, 0)
        commit = self.update(5000)
        with self.assertRaisesRegex(ValueError, 'require at_ms'):
            gateway.notify('u1:0', 'product-1', commit.notification_payload)
        self.assertNotIn('u1:0', gateway.state()['notification_ids'])
        self.assertTrue(gateway.notify(
            'u1:0', 'product-1', commit.notification_payload, at_ms=15,
        ))

    def test_insufficient_update_state_rolls_back_notification(self):
        gateway = CacheGateway(self.workload, 'always-update')
        before = gateway.read('product-1', 0, 0).content_sha256
        with self.assertRaisesRegex(ValueError, 'sufficient state'):
            gateway.notify(
                'u1:0', 'product-1', {'revision': 1}, at_ms=15,
            )
        state = gateway.state()
        self.assertEqual(state['notification_ids'], ())
        self.assertEqual(gateway.cache['product-1'].content_sha256, before)

    def test_write_reactive_updates_when_updates_cost_less(self):
        gateway = CacheGateway(
            self.workload,
            'write-reactive',
            update_cost=1,
            invalidate_cost=1,
            miss_cost=4,
            initial_expected_writes=2,
        )
        gateway.read('product-1', 0, 0)
        commit = self.update(5000)
        gateway.notify('u1:0', 'product-1', commit.notification_payload, at_ms=15)
        result = gateway.read('product-1', 20, 1)
        self.assertTrue(result.semantically_fresh)
        self.assertTrue(result.cache_hit)
        state = gateway.state()
        self.assertEqual(state['last_write_action']['product-1'], 'update')
        self.assertEqual(state['write_history']['product-1']['write_sum'], 1)
        self.assertEqual(state['write_history']['product-1']['sample_count'], 1)

    def test_write_reactive_invalidates_when_updates_cost_more(self):
        gateway = CacheGateway(
            self.workload,
            'write-reactive',
            update_cost=4,
            invalidate_cost=1,
            miss_cost=2,
            initial_expected_writes=1,
        )
        gateway.read('product-1', 0, 0)
        commit = self.update(5000)
        gateway.notify('u1:0', 'product-1', commit.notification_payload, at_ms=15)
        result = gateway.read('product-1', 20, 1)
        self.assertTrue(result.semantically_fresh)
        self.assertFalse(result.cache_hit)
        self.assertEqual(result.origin_operation, 'fetch')
        self.assertEqual(gateway.state()['last_write_action']['product-1'], 'invalidate')

    def test_reset_clears_policy_state_and_replays_fixture(self):
        gateway = CacheGateway(self.workload, 'always-invalidate')
        original = gateway.read('product-1', 0, 0).content_sha256
        commit = self.update(5000)
        gateway.notify('u1:0', 'product-1', commit.notification_payload)
        gateway.read('product-1', 20, 1)
        gateway.reset(0)
        self.assertEqual(gateway.state()['cache_keys'], ())
        self.assertEqual(gateway.state()['notification_ids'], ())
        replayed = gateway.read('product-1', 0, 0)
        self.assertEqual(replayed.content_sha256, original)

    def test_reused_notification_id_with_different_content_fails(self):
        gateway = CacheGateway(self.workload, 'always-invalidate')
        gateway.notify('u1:0', 'product-1', {'revision': 1})
        with self.assertRaisesRegex(ValueError, 'reused'):
            gateway.notify('u1:0', 'product-1', {'revision': 2})

    def test_query_dependency_resolvers_are_conservative(self):
        rendering = '/api/articles?tag=rendering&limit=10&offset=0'
        accessibility = '/api/articles?tag=accessibility&limit=10&offset=0'
        payload = {'previous_tags': ['rendering'], 'current_tags': ['rendering']}
        self.assertTrue(realworld_feed_affects(rendering, 'article-1', payload))
        self.assertFalse(realworld_feed_affects(accessibility, 'article-1', payload))
        self.assertTrue(realworld_feed_affects('/api/articles', 'article-1', payload))

        order_query = '/api/orders?sort=["id","ASC"]&range=[0,9]'
        customer_query = '/api/customers?sort=["id","ASC"]&range=[0,9]'
        self.assertTrue(dashboard_query_affects(
            order_query, 'orders:1', {'resource': 'orders'},
        ))
        self.assertFalse(dashboard_query_affects(
            customer_query, 'orders:1', {'resource': 'orders'},
        ))


if __name__ == '__main__':
    unittest.main()
