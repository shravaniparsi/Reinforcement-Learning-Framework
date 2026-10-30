import json
import tempfile
import unittest
from pathlib import Path

from experiments.freshness.summarize_training_costs import summarize


class FreshnessTrainingCostSummaryTests(unittest.TestCase):
    def test_incomplete_campaign_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, '90 complete blocks'):
                summarize(Path(directory))

    def test_duplicate_block_identity_is_rejected_before_cost_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = {
                'passed': True,
                'stage': 'training',
                'block_identity': {
                    'workload': 'mutable-product-v1',
                    'regime': 'balanced',
                    'trace_seed': 100,
                },
                'attempts': [],
            }
            for index in range(90):
                path = root / str(index)
                path.mkdir()
                (path / 'manifest.json').write_text(json.dumps(manifest))
                (path / 'schedule.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                summarize(root)


if __name__ == '__main__':
    unittest.main()
