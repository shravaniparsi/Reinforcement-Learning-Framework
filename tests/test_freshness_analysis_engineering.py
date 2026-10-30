import unittest
from pathlib import Path

from experiments.freshness.run_analysis_engineering import run


FIXTURE = Path('experiments/freshness/analysis_fixture_v1.json')


class FreshnessAnalysisEngineeringTests(unittest.TestCase):
    def test_fixture_exercises_selection_intervals_and_pool_expansion(self):
        artifact = run(FIXTURE)
        self.assertEqual(artifact['selected_candidate'], 'ttl-50')
        self.assertEqual(len(artifact['primary_intervals']), 5)
        self.assertTrue(artifact['requires_reserved_pool_expansion'])
        self.assertFalse(artifact['contains_application_study_observations'])


if __name__ == '__main__':
    unittest.main()
