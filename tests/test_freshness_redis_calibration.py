import unittest

from experiments.freshness.redis_calibration import RESPConnection, _percentile, summarize


class RedisCalibrationTests(unittest.TestCase):
    def test_resp_command_encoding(self):
        self.assertEqual(
            RESPConnection.encode_command(('SET', 'key', b'value')),
            b'*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n$5\r\nvalue\r\n',
        )

    def test_nearest_rank_percentile_and_summary(self):
        values = list(range(1, 101))
        self.assertEqual(_percentile(values, 0.50), 50)
        self.assertEqual(_percentile(values, 0.99), 99)
        result = summarize(values)
        self.assertEqual(result['count'], 100)
        self.assertEqual(result['p95_ns'], 95)
        self.assertEqual(result['max_ns'], 100)

    def test_summary_rejects_invalid_values(self):
        with self.assertRaises(ValueError):
            summarize([])
        with self.assertRaises(ValueError):
            summarize([1, -1])


if __name__ == '__main__':
    unittest.main()
