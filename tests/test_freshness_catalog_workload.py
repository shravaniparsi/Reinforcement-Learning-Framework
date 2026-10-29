import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))

from freshness.catalog_workload import CatalogWorkload


class CatalogWorkloadTests(unittest.TestCase):
    def setUp(self):
        self.workload = CatalogWorkload(product_count=4)

    def tearDown(self):
        self.workload.close()

    def test_commit_preserves_historical_oracle_and_other_product_revision(self):
        original = self.workload.read('product-1')
        other_before = self.workload.read('product-2')
        commit = self.workload.commit(
            {'key': 'product-1', 'changes': {'price_cents': 4999, 'available': False}},
            at_ms=25,
        )
        current = self.workload.read('product-1')
        historical = self.workload.oracle('product-1', 0)

        self.assertEqual(commit.revision, 1)
        self.assertEqual(current.content['price_cents'], 4999)
        self.assertFalse(current.content['available'])
        self.assertEqual(historical.content_sha256, original.content_sha256)
        self.assertEqual(self.workload.read('product-2').served_revision, other_before.served_revision)

    def test_conditional_validator_reports_no_body_transfer(self):
        first = self.workload.read('product-1')
        validated = self.workload.read('product-1', validator=first.validator)
        self.assertTrue(validated.not_modified)
        self.assertEqual(validated.response_body_bytes, 0)
        self.assertEqual(validated.content_sha256, first.content_sha256)

        self.workload.commit({'key': 'product-1', 'changes': {'price_cents': 2000}}, at_ms=1)
        changed = self.workload.read('product-1', validator=first.validator)
        self.assertFalse(changed.not_modified)
        self.assertGreater(changed.response_body_bytes, 0)

    def test_reset_is_deterministic_and_seed_changes_fixture(self):
        initial = self.workload.read('product-1').content_sha256
        self.workload.commit({'key': 'product-1', 'changes': {'price_cents': 9999}}, at_ms=1)
        self.workload.reset(seed=0)
        self.assertEqual(self.workload.read('product-1').content_sha256, initial)
        self.workload.reset(seed=1)
        self.assertNotEqual(self.workload.read('product-1').content_sha256, initial)

    def test_invalid_mutation_does_not_change_revision(self):
        before = self.workload.read('product-1')
        with self.assertRaisesRegex(ValueError, 'price_cents'):
            self.workload.commit(
                {'key': 'product-1', 'changes': {'price_cents': -1}}, at_ms=10
            )
        after = self.workload.read('product-1')
        self.assertEqual(after.content_sha256, before.content_sha256)
        self.assertEqual(after.served_revision, before.served_revision)


if __name__ == '__main__':
    unittest.main()
