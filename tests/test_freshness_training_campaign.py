import unittest
from pathlib import Path

from experiments.freshness.training_campaign import TrainingCampaign


class FreshnessTrainingCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.campaign = TrainingCampaign.load(
            Path('experiments/freshness/training_campaign_v1.json'),
            Path('experiments/freshness/parameter_grid_v1.json'),
            Path('experiments/freshness/trace_design_v1.json'),
        )

    def test_candidate_counts_and_declared_order(self):
        self.assertEqual(len(self.campaign.candidates('fixed-ttl')), 6)
        self.assertEqual(len(self.campaign.candidates('stale-while-revalidate')), 36)
        self.assertEqual(len(self.campaign.candidates('event-invalidate-with-repair')), 6)
        self.assertEqual(len(self.campaign.candidates('write-reactive')), 6)
        for policy in (
            'fixed-ttl', 'stale-while-revalidate',
            'event-invalidate-with-repair', 'write-reactive',
        ):
            candidates = self.campaign.candidates(policy)
            self.assertEqual(
                [item.declared_order for item in candidates], list(range(len(candidates))),
            )
            self.assertEqual(len({item.candidate_id for item in candidates}), len(candidates))

    def test_exact_campaign_unit_counts(self):
        self.assertEqual(self.campaign.expected_unit_counts(), {
            'cost-calibration': 720,
            'time-candidates': 4320,
            'event-candidates-and-controls': 12960,
        })

    def test_campaign_excludes_final_test(self):
        self.assertFalse(self.campaign.source['final_test_authorized'])
        self.assertEqual(self.campaign.source['partition'], 'training')


if __name__ == '__main__':
    unittest.main()
