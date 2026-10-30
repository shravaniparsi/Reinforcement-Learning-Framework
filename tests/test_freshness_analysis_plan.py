import unittest

from experiments.freshness.analysis_plan import (
    CandidateSummary,
    paired_bootstrap_mean_interval,
    paired_differences,
    required_trace_count,
    reserved_pool_is_sufficient,
    select_candidate,
)


class FreshnessAnalysisPlanTests(unittest.TestCase):
    def test_selection_prioritizes_freshness_then_bytes_then_declared_order(self):
        candidates = (
            CandidateSummary('fast-stale', 0.030, 100, 0),
            CandidateSummary('fresh-heavy', 0.010, 500, 1),
            CandidateSummary('within-margin', 0.019, 200, 2),
            CandidateSummary('same-bytes-later', 0.018, 200, 3),
        )
        self.assertEqual(select_candidate(candidates).name, 'within-margin')

    def test_candidate_outside_one_point_margin_is_ineligible(self):
        candidates = (
            CandidateSummary('fresh', 0.010, 1000, 0),
            CandidateSummary('outside', 0.020001, 1, 1),
        )
        self.assertEqual(select_candidate(candidates).name, 'fresh')

    def test_paired_differences_require_identical_trace_units(self):
        result = paired_differences({'a': 0.2, 'b': 0.5}, {'a': 0.1, 'b': 0.3})
        self.assertEqual(result, (0.1, 0.2))
        with self.assertRaisesRegex(ValueError, 'identities differ'):
            paired_differences({'a': 1.0}, {'b': 1.0})

    def test_bootstrap_is_deterministic_and_resamples_trace_units(self):
        values = (-0.03, -0.02, -0.01, 0.0, -0.04, -0.02, -0.01, -0.03)
        first = paired_bootstrap_mean_interval(values, seed=29)
        second = paired_bootstrap_mean_interval(values, seed=29)
        self.assertEqual(first, second)
        self.assertEqual(first.n, 8)
        self.assertEqual(first.confidence, 0.99)
        self.assertLess(first.upper, 0)

    def test_precision_rule_uses_largest_requirement_and_expands_if_needed(self):
        low_variance = [0.009, 0.010, 0.011, 0.010, 0.009, 0.011, 0.010, 0.010]
        high_variance = [-0.03, 0.04, -0.02, 0.05, -0.04, 0.03, -0.01, 0.06]
        low_n = required_trace_count(low_variance, 0.01)
        high_n = required_trace_count(high_variance, 0.01)
        self.assertEqual(low_n, 8)
        self.assertGreater(high_n, low_n)
        self.assertTrue(reserved_pool_is_sufficient(low_n))
        self.assertFalse(reserved_pool_is_sufficient(max(21, high_n)))


if __name__ == '__main__':
    unittest.main()
