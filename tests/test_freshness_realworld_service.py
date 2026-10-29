import json
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))

from freshness.realworld_service import CONTROL_HEADER, CONTROL_VALUE, server
from freshness.realworld_workload import RealWorldFeedWorkload


class RealWorldServiceTests(unittest.TestCase):
    def setUp(self):
        self.workload = RealWorldFeedWorkload(article_count=30)
        self.httpd = server(0, self.workload)
        self.base = f'http://127.0.0.1:{self.httpd.server_port}'
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)
        self.workload.close()

    def get(self, path, headers=None):
        request = Request(self.base + path, headers=headers or {})
        with urlopen(request, timeout=5) as response:
            return response.status, dict(response.headers), json.load(response)

    def post(self, path, value, authorized=True):
        headers = {'Content-Type': 'application/json'}
        if authorized:
            headers[CONTROL_HEADER] = CONTROL_VALUE
        request = Request(
            self.base + path,
            data=json.dumps(value).encode('utf-8'),
            headers=headers,
            method='POST',
        )
        with urlopen(request, timeout=5) as response:
            return response.status, json.load(response)

    def test_feed_etag_and_conditional_validation(self):
        status, headers, content = self.get('/api/articles?tag=rendering&limit=10&offset=0')
        self.assertEqual(status, 200)
        self.assertEqual(content['articlesCount'], 15)
        with self.assertRaises(HTTPError) as captured:
            self.get(
                '/api/articles?tag=rendering&limit=10&offset=0',
                headers={'If-None-Match': headers['ETag']},
            )
        self.assertEqual(captured.exception.code, 304)
        self.assertEqual(captured.exception.headers['ETag'], headers['ETag'])

    def test_authorized_commit_changes_visible_feed(self):
        _, headers, before = self.get('/api/articles?tag=rendering&limit=10&offset=0')
        status, commit = self.post(
            '/control/commit',
            {
                'at_ms': 50,
                'operation': 'update',
                'slug': 'independent-note-28',
                'changes': {'title': 'Controlled update'},
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(commit['revision'], 1)
        _, after_headers, after = self.get(
            '/api/articles?tag=rendering&limit=10&offset=0',
            headers={'If-None-Match': headers['ETag']},
        )
        self.assertEqual(after['articles'][0]['title'], 'Controlled update')
        self.assertNotEqual(after_headers['ETag'], headers['ETag'])

    def test_browser_style_control_request_is_rejected(self):
        request = Request(
            self.base + '/control/reset',
            data=b'{"seed":0}',
            headers={CONTROL_HEADER: CONTROL_VALUE, 'Origin': 'http://127.0.0.1:3105'},
            method='POST',
        )
        with self.assertRaises(HTTPError) as captured:
            urlopen(request, timeout=5)
        self.assertEqual(captured.exception.code, 403)

    def test_reset_restores_declared_fixture(self):
        self.post(
            '/control/commit',
            {
                'at_ms': 25,
                'operation': 'delete',
                'slug': 'independent-note-29',
            },
        )
        _, _, changed = self.get('/api/articles')
        self.assertEqual(changed['articlesCount'], 29)
        self.post('/control/reset', {'seed': 0})
        _, headers, reset = self.get('/api/articles')
        self.assertEqual(reset['articlesCount'], 30)
        self.assertEqual(headers['X-Origin-Revision'], '0')


if __name__ == '__main__':
    unittest.main()
