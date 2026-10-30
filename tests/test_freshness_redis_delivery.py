import unittest

from experiments.freshness.redis_delivery import RedisNotificationTransport


class RedisNotificationTransportTests(unittest.TestCase):
    def test_payload_is_canonical_and_identity_bound(self):
        first = RedisNotificationTransport._payload('n1', 'key', {'b': 2, 'a': 1})
        second = RedisNotificationTransport._payload('n1', 'key', {'a': 1, 'b': 2})
        changed = RedisNotificationTransport._payload('n2', 'key', {'a': 1, 'b': 2})
        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)

    def test_real_delivery_preserves_payload_for_both_modes(self):
        for mode in ('redis-pubsub', 'redis-streams'):
            with self.subTest(mode=mode):
                try:
                    transport_context = RedisNotificationTransport(mode)
                except PermissionError:
                    self.skipTest('local sandbox does not allow loopback sockets')
                with transport_context as transport:
                    transport.reset()
                    result = transport.deliver('n1', 'product-1', {'revision': 1})
                    self.assertEqual(result.notification_id, 'n1')
                    self.assertEqual(result.mode, mode)
                    self.assertGreater(result.payload_bytes, 0)
                    self.assertGreater(result.wall_ns, 0)
                    self.assertGreaterEqual(result.thread_cpu_ns, 0)
