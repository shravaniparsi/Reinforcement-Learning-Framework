import json
import unittest
from urllib.parse import urlencode

from experiments.freshness.dashboard_workload import DashboardWorkload


def query(resource, filters=None, sort=None, item_range=None):
    return f'/api/{resource}?' + urlencode({
        'filter': json.dumps(filters or {}),
        'sort': json.dumps(sort or ['id', 'ASC']),
        'range': json.dumps(item_range or [0, 99]),
    })


class DashboardWorkloadTests(unittest.TestCase):
    def setUp(self):
        self.workload = DashboardWorkload()

    def test_resource_queries_filter_sort_and_page(self):
        orders = self.workload.read(query(
            'orders', {'status': 'ordered'}, ['date', 'DESC'], [0, 2],
        )).content
        self.assertEqual(orders['total'], 4)
        self.assertEqual([record['id'] for record in orders['records']], [3, 6, 9])

        customers = self.workload.read(query(
            'customers', {'id': ['1', '3', '5']}, ['id', 'ASC'], [0, 99],
        )).content
        self.assertEqual([record['id'] for record in customers['records']], [1, 3, 5])

    def test_conditional_validator_uses_complete_query_content(self):
        key = query('reviews', {'status': 'pending'}, ['date', 'DESC'], [0, 99])
        first = self.workload.read(key)
        second = self.workload.read(key, first.validator)
        self.assertTrue(second.not_modified)
        self.assertEqual(second.response_body_bytes, 0)

        self.workload.commit({
            'resource': 'orders', 'operation': 'update', 'id': 1,
            'changes': {'total': 999},
        }, at_ms=1)
        unrelated = self.workload.read(key, first.validator)
        self.assertTrue(unrelated.not_modified)
        self.assertEqual(unrelated.decision_revision, 1)

    def test_historical_oracle_survives_update_and_delete(self):
        key = query('reviews', {'status': 'pending'}, ['date', 'DESC'], [0, 99])
        before = self.workload.oracle(key, 0)
        record = self.workload.commit({
            'resource': 'reviews', 'operation': 'update', 'id': 1,
            'changes': {'status': 'accepted'},
        }, at_ms=10)
        self.assertEqual(record.revision, 1)
        self.assertNotEqual(self.workload.oracle(key, 1).content_sha256, before.content_sha256)
        self.assertEqual(self.workload.oracle(key, 0), before)

        self.workload.commit({
            'resource': 'reviews', 'operation': 'delete', 'id': 2,
        }, at_ms=20)
        all_reviews = self.workload.oracle(query('reviews'), 2).content
        self.assertNotIn(2, [item['id'] for item in all_reviews['records']])
        self.assertIn(2, [item['id'] for item in self.workload.oracle(query('reviews'), 0).content['records']])

    def test_dashboard_oracle_is_one_complete_revision(self):
        before = self.workload.dashboard_oracle(0)
        self.assertEqual(before.content['pending_review_count'], 3)
        self.assertEqual(len(before.content['pending_reviews']), 3)
        self.assertEqual(
            set(before.content['referenced_customers']),
            {'1', '3', '4', '5', '6'},
        )

        self.workload.commit({
            'resource': 'orders', 'operation': 'update', 'id': 1,
            'changes': {'total': 999},
        }, at_ms=10)
        after = self.workload.dashboard_oracle(1)
        self.assertEqual(after.content['revenue'] - before.content['revenue'], 952)
        self.assertEqual(self.workload.dashboard_oracle(0), before)

    def test_create_and_reset_are_deterministic(self):
        base = self.workload.oracle(query('customers'), 0)
        self.workload.commit({
            'resource': 'customers', 'operation': 'create',
            'record': {
                'id': 9,
                'first_name': 'Created',
                'last_name': 'Customer',
                'avatar': 'data:image/svg+xml,fixture',
                'first_seen': '2026-10-29T10:00:00.000Z',
                'has_ordered': True,
            },
        }, at_ms=30)
        self.assertEqual(self.workload.read(query('customers')).content['total'], 9)
        self.workload.reset(0)
        self.assertEqual(self.workload.oracle(query('customers'), 0), base)

    def test_rejects_unknown_query_and_record_fields(self):
        with self.assertRaises(ValueError):
            self.workload.read('/api/products')
        with self.assertRaises(ValueError):
            self.workload.commit({
                'resource': 'orders', 'operation': 'update', 'id': 1,
                'changes': {'unknown': 1},
            }, at_ms=1)


if __name__ == '__main__':
    unittest.main()
