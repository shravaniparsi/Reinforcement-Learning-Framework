import unittest
from pathlib import Path

from experiments.freshness.cache_gateway import CacheGateway
from experiments.freshness.catalog_workload import CatalogWorkload
from experiments.freshness.measurement import summarize_trace_run
from experiments.freshness.trace_generator import TraceDesign, generate_schedule
from experiments.freshness.trace_runner import run_trace


class FreshnessMeasurementTests(unittest.TestCase):
    def test_summary_uses_one_request_measurement_per_observation(self):
        design = TraceDesign.load(Path('experiments/freshness/trace_design_v1.json'))
        schedule = generate_schedule(
            design,
            workload_id='mutable-product-v1',
            regime='write-intensive',
            partition='engineering',
            seed=0,
            fault_profile='no-fault',
            transport_mode='redis-pubsub',
        )
        workload = CatalogWorkload(product_count=20)
        try:
            run = run_trace(schedule, CacheGateway(workload, 'bypass'))
        finally:
            workload.close()
        summary = summarize_trace_run(run)
        self.assertEqual(summary['request_count'], 100)
        self.assertEqual(summary['freshness_violation_count'], 0)
        self.assertEqual(summary['origin_operations'], {'fetch': 100})
        self.assertGreater(summary['request_wall_ns']['p99'], 0)
        self.assertEqual(summary['redis_delivery_payload_bytes'], 0)


if __name__ == '__main__':
    unittest.main()
