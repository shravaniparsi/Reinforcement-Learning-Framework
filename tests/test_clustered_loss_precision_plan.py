import json
import tempfile
import unittest
from pathlib import Path

from scripts.analyze_clustered_loss_precision import _load_plan, _project_widths


ROOT = Path(__file__).resolve().parents[1]


class ClusteredLossPrecisionPlanTests(unittest.TestCase):
    def test_locked_plan_contract(self):
        path = ROOT / "experiments/freshness/clustered_loss_precision_plan_v1.json"
        plan = _load_plan(path)
        self.assertEqual(plan["planning_seed_start"], 2100)
        self.assertEqual(plan["planning_seed_count"], 10)
        self.assertEqual(plan["candidate_final_seed_counts"], [12, 18, 24, 30, 36, 48])
        self.assertFalse(plan["final_collection_authorized"])

    def test_projection_width_decreases_with_final_seed_count(self):
        result = _project_widths(
            [0.00, 0.01, -0.01, 0.02, -0.02, 0.01, 0.00, -0.01, 0.01, 0.00],
            [12, 18, 24],
            0.95,
            0.90,
        )
        widths = result["projected_full_width"]
        self.assertGreater(widths["12"], widths["18"])
        self.assertGreater(widths["18"], widths["24"])
        self.assertTrue(result["stable"])

    def test_zero_variance_does_not_authorize_selection(self):
        result = _project_widths([0.0] * 10, [12, 18], 0.95, 0.90)
        self.assertFalse(result["stable"])
        self.assertEqual(result["projected_full_width"], {})

    def test_plan_rejects_authorized_final_collection(self):
        source = json.loads(
            (ROOT / "experiments/freshness/clustered_loss_precision_plan_v1.json").read_text()
        )
        source["final_collection_authorized"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps(source))
            with self.assertRaises(ValueError):
                _load_plan(path)


if __name__ == "__main__":
    unittest.main()
