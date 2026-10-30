import unittest
from pathlib import Path

from experiments.freshness.parameter_design import ParameterGrid


GRID_PATH = Path('experiments/freshness/parameter_grid_v1.json')


class FreshnessParameterDesignTests(unittest.TestCase):
    def test_grid_loads_with_stable_identity(self):
        first = ParameterGrid.load(GRID_PATH)
        second = ParameterGrid.load(GRID_PATH)
        self.assertEqual(first.digest(), second.digest())
        self.assertEqual(first.fixed_ttl_ms, (10, 25, 50, 100, 250, 500))

    def test_final_partition_cannot_fit_or_confirm_parameters(self):
        grid = ParameterGrid.load(GRID_PATH)
        self.assertEqual(grid.selection_partitions['fit'], 'training')
        self.assertEqual(grid.selection_partitions['confirm'], 'validation')
        self.assertEqual(grid.selection_partitions['locked_evaluation'], 'final-test')
        self.assertNotIn(
            grid.selection_partitions['locked_evaluation'],
            (grid.selection_partitions['fit'], grid.selection_partitions['confirm']),
        )

    def test_write_reactive_costs_are_observed_bytes_not_weights(self):
        grid = ParameterGrid.load(GRID_PATH)
        self.assertEqual(grid.cost_basis, 'serialized-bytes')
        self.assertTrue(all('bytes' in source for source in grid.cost_sources.values()))


if __name__ == '__main__':
    unittest.main()
