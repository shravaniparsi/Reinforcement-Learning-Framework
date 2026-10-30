import tempfile
import unittest
from pathlib import Path

from experiments.freshness.select_time_candidates import select


class FreshnessTimeSelectionTests(unittest.TestCase):
    def test_incomplete_campaign_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, '90 blocks'):
                select(Path(directory))


if __name__ == '__main__':
    unittest.main()
