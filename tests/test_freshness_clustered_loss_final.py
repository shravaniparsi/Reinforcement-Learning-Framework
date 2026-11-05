import json
import random
import tempfile
import unittest
from pathlib import Path

from experiments.freshness.clustered_loss_design import generate_clustered_schedule
from experiments.freshness.clustered_loss_final_design import (
    ClusteredLossFinalDesign,
    FINAL_STAGE,
)
from experiments.freshness.trace_generator import TraceDesign
from scripts.analyze_clustered_loss_final import (
    _artifact_name_pattern,
    _bootstrap_interval,
    _expected_shard_by_seed,
    _load_archive_inventories,
    _load_protocol,
)
from scripts.build_clustered_loss_final_matrix import build


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments/freshness"
PROTOCOL_PATH = PACKAGE / "clustered_loss_final_protocol_v1.json"


class ClusteredLossFinalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = TraceDesign.load(PACKAGE / "trace_design_v2.json")
        cls.protocol = _load_protocol(PROTOCOL_PATH)
        cls.design = ClusteredLossFinalDesign.load(
            PACKAGE / "clustered_loss_final_design_v1.json",
            cls.base,
            PROTOCOL_PATH,
        )

    def test_authorized_design_contains_only_final_range(self):
        identity = {
            "stage": FINAL_STAGE,
            "workload": "mutable-product-v1",
            "regime": "balanced",
            "trace_seed": 2200,
            "fault_profile": "single-burst-10",
            "transport": "redis-pubsub",
        }
        self.assertTrue(self.design.contains(identity))
        self.assertFalse(self.design.contains({**identity, "trace_seed": 2100}))
        self.assertFalse(self.design.contains({**identity, "trace_seed": 2284}))
        self.assertFalse(self.design.contains({**identity, "stage": "extension-precision-planning"}))

    def test_final_schedule_uses_final_identity_and_fixed_fault_budget(self):
        schedule = generate_clustered_schedule(
            self.design,
            self.base,
            workload_id="mutable-product-v1",
            regime="balanced",
            partition=FINAL_STAGE,
            seed=2200,
            fault_profile="single-burst-10",
            transport_mode="redis-pubsub",
        )
        self.assertTrue(
            schedule.trace_id.startswith(
                "freshness-clustered-loss-final-v1:extension-final:"
            )
        )
        self.assertEqual(len(schedule.faults), 10)
        self.assertTrue(all(fault.drop for fault in schedule.faults))

    def test_six_matrices_cover_the_final_factorial_once(self):
        identities = []
        for shard in range(1, 7):
            matrix = build(PROTOCOL_PATH, shard)["include"]
            self.assertEqual(len(matrix), 252)
            self.assertTrue(all(item["shard"] == shard for item in matrix))
            identities.extend(
                (
                    item["workload"],
                    item["regime"],
                    item["transport"],
                    item["seed"],
                )
                for item in matrix
            )
        self.assertEqual(len(identities), 1512)
        self.assertEqual(len(identities), len(set(identities)))

    def test_seed_to_shard_contract_covers_84_seeds(self):
        mapping = _expected_shard_by_seed(self.protocol)
        self.assertEqual(len(mapping), 84)
        self.assertEqual(mapping[2200], 1)
        self.assertEqual(mapping[2283], 6)

    def test_artifact_name_contract(self):
        name = (
            "clustered-loss-final-s1-mutable-product-v1-balanced-"
            "redis-pubsub-2200-123456789.zip"
        )
        self.assertIsNotNone(_artifact_name_pattern().match(name))
        self.assertIsNone(
            _artifact_name_pattern().match(
                name.replace("clustered-loss-final", "clustered-loss-precision")
            )
        )

    def test_bootstrap_interval_is_deterministic_and_reports_seed_signs(self):
        first = _bootstrap_interval(
            [-0.2, 0.0, 0.1, 0.3],
            replicates=1000,
            confidence=0.95,
            rng=random.Random(7),
        )
        second = _bootstrap_interval(
            [-0.2, 0.0, 0.1, 0.3],
            replicates=1000,
            confidence=0.95,
            rng=random.Random(7),
        )
        self.assertEqual(first, second)
        self.assertEqual(first["trace_seeds"], 4)
        self.assertEqual(first["positive_seed_estimates"], 2)
        self.assertEqual(first["zero_seed_estimates"], 1)
        self.assertEqual(first["negative_seed_estimates"], 1)

    def test_archive_inventories_require_github_digest_agreement(self):
        run_map = {shard: str(9000 + shard) for shard in range(1, 7)}
        digest = "a" * 64
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for shard in range(1, 7):
                target = root / f"shard-{shard}"
                target.mkdir()
                artifacts = [
                    {
                        "name": f"clustered-loss-final-s{shard}-item-{index}",
                        "archive_sha256": digest,
                        "github_digest": f"sha256:{digest}",
                    }
                    for index in range(252)
                ]
                inventory = {
                    "workflow_run_id": int(run_map[shard]),
                    "artifact_count": 252,
                    "artifact_prefix": f"clustered-loss-final-s{shard}-",
                    "artifacts": artifacts,
                }
                (target / "archive_inventory.json").write_text(
                    json.dumps(inventory), encoding="utf-8"
                )
            records = _load_archive_inventories(root, run_map)
            self.assertEqual(len(records), 1512)
            inventory_path = root / "shard-6/archive_inventory.json"
            invalid = json.loads(inventory_path.read_text(encoding="utf-8"))
            invalid["artifacts"][0]["github_digest"] = "sha256:" + "b" * 64
            inventory_path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "GitHub digest mismatch"):
                _load_archive_inventories(root, run_map)

    def test_design_rejects_revoked_authorization(self):
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        protocol["collection_authorized"] = False
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protocol.json"
            path.write_text(json.dumps(protocol), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not authorize"):
                ClusteredLossFinalDesign.load(
                    PACKAGE / "clustered_loss_final_design_v1.json",
                    self.base,
                    path,
                )


if __name__ == "__main__":
    unittest.main()
