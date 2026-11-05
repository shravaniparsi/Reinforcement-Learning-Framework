import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T_CRITICAL_95_DF83 = 1.988959780175162


class ClusteredLossFinalProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = (
            ROOT
            / "experiments/freshness/clustered_loss_final_protocol_v1.json"
        )
        cls.protocol = json.loads(path.read_text(encoding="utf-8"))

    def test_protocol_authorizes_collection_after_author_approval(self):
        self.assertEqual(
            self.protocol["status"], "authorized-prospective"
        )
        self.assertTrue(self.protocol["collection_authorized"])

    def test_final_seeds_are_fresh_and_complete(self):
        provenance = self.protocol["planning_provenance"]
        planning = set(
            range(
                provenance["planning_seed_start"],
                provenance["planning_seed_start"] + provenance["planning_seed_count"],
            )
        )
        final = set(
            range(
                self.protocol["final_seed_start"],
                self.protocol["final_seed_stop_exclusive"],
            )
        )
        self.assertEqual(len(final), self.protocol["final_seed_count"])
        self.assertFalse(planning & final)

    def test_shards_cover_every_final_seed_once(self):
        seeds = []
        for shard in self.protocol["collection_shards"]:
            seeds.extend(
                range(shard["seed_start"], shard["seed_start"] + shard["seed_count"])
            )
        self.assertEqual(len(seeds), self.protocol["final_seed_count"])
        self.assertEqual(len(seeds), len(set(seeds)))
        self.assertEqual(min(seeds), self.protocol["final_seed_start"])
        self.assertEqual(max(seeds) + 1, self.protocol["final_seed_stop_exclusive"])
        self.assertTrue(all(shard["seed_count"] * 18 <= 256 for shard in self.protocol["collection_shards"]))

    def test_family_envelopes_meet_original_targets_at_84_seeds(self):
        rule = self.protocol["sample_size_rule"]
        n = rule["selected_seed_count"]
        targets = self.protocol["precision_targets_full_width"]
        projected = rule["projected_full_width_at_selected_count"]
        for family, sigma in rule["family_variance_envelope"].items():
            width = 2.0 * T_CRITICAL_95_DF83 * sigma / math.sqrt(n)
            self.assertAlmostEqual(
                width, projected[f"{family}_family_envelope"], places=15
            )
        self.assertLessEqual(
            projected["freshness_family_envelope"],
            targets["repair_vs_always_freshness_interaction"],
        )
        self.assertLessEqual(
            projected["persistence10_family_envelope"],
            targets["repair_vs_always_persistence10_interaction"],
        )

    def test_job_accounting_matches_fixed_factorial(self):
        self.assertEqual(self.protocol["strata_per_seed"], 18)
        self.assertEqual(
            self.protocol["total_jobs"],
            self.protocol["final_seed_count"] * self.protocol["strata_per_seed"],
        )
        self.assertTrue(
            all(
                shard["seed_count"] * self.protocol["strata_per_seed"]
                == self.protocol["jobs_per_shard"]
                for shard in self.protocol["collection_shards"]
            )
        )


if __name__ == "__main__":
    unittest.main()
