import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))

from freshness.realworld_workload import RealWorldFeedWorkload, parse_feed_query


class RealWorldFeedWorkloadTests(unittest.TestCase):
    def setUp(self):
        self.workload = RealWorldFeedWorkload(article_count=30)

    def tearDown(self):
        self.workload.close()

    def test_initial_feed_matches_pinned_fixture_order(self):
        response = self.workload.read('tag=&limit=10&offset=0')
        self.assertEqual(response.content['articlesCount'], 30)
        self.assertEqual(response.content['articles'][0]['slug'], 'independent-note-29')
        rendering = self.workload.read('/api/articles?tag=rendering&limit=10&offset=0')
        self.assertEqual(rendering.content['articlesCount'], 15)
        self.assertTrue(all('rendering' in article['tagList'] for article in rendering.content['articles']))

    def test_update_preserves_historical_query_snapshot(self):
        query = 'tag=rendering&limit=10&offset=0'
        original = self.workload.read(query)
        commit = self.workload.commit(
            {
                'operation': 'update',
                'slug': 'independent-note-28',
                'changes': {'title': 'Updated rendering article'},
            },
            at_ms=50,
        )
        current = self.workload.read(query)
        historical = self.workload.oracle(query, original.decision_revision)
        self.assertEqual(commit.revision, 1)
        self.assertNotEqual(current.content_sha256, original.content_sha256)
        self.assertEqual(historical.content_sha256, original.content_sha256)
        self.assertEqual(current.content['articles'][0]['title'], 'Updated rendering article')

    def test_tag_change_moves_membership_and_updates_counts(self):
        before_rendering = self.workload.read('tag=rendering&limit=20&offset=0')
        before_accessibility = self.workload.read('tag=accessibility&limit=20&offset=0')
        self.workload.commit(
            {
                'operation': 'update',
                'slug': 'independent-note-28',
                'changes': {'tagList': ['accessibility']},
            },
            at_ms=75,
        )
        after_rendering = self.workload.read('tag=rendering&limit=20&offset=0')
        after_accessibility = self.workload.read('tag=accessibility&limit=20&offset=0')
        self.assertEqual(after_rendering.content['articlesCount'], before_rendering.content['articlesCount'] - 1)
        self.assertEqual(after_accessibility.content['articlesCount'], before_accessibility.content['articlesCount'] + 1)

    def test_create_and_delete_have_historical_oracles(self):
        query = 'tag=rendering&limit=10&offset=0'
        initial = self.workload.read(query)
        self.workload.commit(
            {
                'operation': 'create',
                'article': {
                    'slug': 'new-rendering-note',
                    'title': 'New rendering note',
                    'description': 'New description',
                    'body': 'New body',
                    'tagList': ['rendering'],
                    'created_seq': 100,
                },
            },
            at_ms=100,
        )
        created = self.workload.read(query)
        self.assertEqual(created.content['articles'][0]['slug'], 'new-rendering-note')
        created_revision = created.decision_revision
        self.workload.commit(
            {'operation': 'delete', 'slug': 'new-rendering-note'}, at_ms=200
        )
        deleted = self.workload.read(query)
        self.assertNotIn('new-rendering-note', [item['slug'] for item in deleted.content['articles']])
        self.assertEqual(
            self.workload.oracle(query, created_revision).content_sha256,
            created.content_sha256,
        )
        self.assertEqual(
            self.workload.oracle(query, initial.decision_revision).content_sha256,
            initial.content_sha256,
        )

    def test_unchanged_query_reuses_validator_after_unrelated_update(self):
        query = 'tag=rendering&limit=20&offset=0'
        before = self.workload.read(query)
        self.workload.commit(
            {
                'operation': 'update',
                'slug': 'independent-note-29',
                'changes': {'title': 'Accessibility-only update'},
            },
            at_ms=30,
        )
        validated = self.workload.read(query, validator=before.validator)
        self.assertGreater(validated.decision_revision, before.decision_revision)
        self.assertTrue(validated.not_modified)
        self.assertEqual(validated.response_body_bytes, 0)
        self.assertEqual(validated.content_sha256, before.content_sha256)

    def test_query_parser_rejects_ambiguous_or_unknown_inputs(self):
        self.assertEqual(parse_feed_query(''), ('tag=&limit=10&offset=0', None, 10, 0))
        self.assertEqual(
            parse_feed_query('/api/articles?offset=0&limit=10&tag=rendering'),
            ('tag=rendering&limit=10&offset=0', 'rendering', 10, 0),
        )
        with self.assertRaises(ValueError):
            parse_feed_query('tag=rendering&tag=accessibility')
        with self.assertRaises(ValueError):
            parse_feed_query('sort=popular')


if __name__ == '__main__':
    unittest.main()
