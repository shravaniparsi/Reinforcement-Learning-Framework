import unittest
from dataclasses import replace
from pathlib import Path

from experiments.freshness.cache_gateway import CacheGateway
from experiments.freshness.catalog_workload import CatalogWorkload
from experiments.freshness.clustered_loss_design import ClusteredLossDesign, generate_clustered_schedule
from experiments.freshness.clustered_loss_measurement import summarize_clustered_loss
from experiments.freshness.trace_generator import TraceDesign
from experiments.freshness.trace_runner import run_trace


PACKAGE = Path('experiments/freshness')


class ClusteredLossMeasurementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = TraceDesign.load(PACKAGE / 'trace_design_v2.json')
        cls.design = ClusteredLossDesign.load(PACKAGE / 'clustered_loss_design_v1.json', cls.base)

    def schedule(self, profile):
        return generate_clustered_schedule(
            self.design, self.base,
            workload_id='mutable-product-v1', regime='write-intensive',
            partition='extension-engineering', seed=2000,
            fault_profile=profile, transport_mode='redis-pubsub',
        )

    def test_no_fault_fresh_policy_has_zero_episode_and_recovery_outcomes(self):
        schedule = self.schedule('no-fault')
        workload = CatalogWorkload(product_count=20)
        try:
            run = run_trace(schedule, CacheGateway(workload, 'conditional-validation'))
        finally:
            workload.close()
        summary = summarize_clustered_loss(run, schedule)
        self.assertEqual(summary['stale_episode_count'], 0)
        self.assertEqual(summary['max_consecutive_stale_requests'], 0)
        self.assertEqual(summary['requests_until_observed_terminal_recovery'], 0)
        self.assertFalse(summary['terminal_recovery_right_censored'])

    def test_episode_metrics_count_consecutive_stale_requests(self):
        schedule = self.schedule('single-burst-10')
        workload = CatalogWorkload(product_count=20)
        try:
            run = run_trace(schedule, CacheGateway(workload, 'conditional-validation'))
        finally:
            workload.close()
        observations = list(run.observations)
        observations[1] = replace(observations[1], semantically_fresh=False)
        observations[2] = replace(observations[2], semantically_fresh=False)
        observations[5] = replace(observations[5], semantically_fresh=False)
        altered = replace(run, observations=tuple(observations))
        summary = summarize_clustered_loss(altered, schedule)
        self.assertEqual(summary['stale_episode_count'], 2)
        self.assertEqual(summary['max_consecutive_stale_requests'], 2)


if __name__ == '__main__':
    unittest.main()
