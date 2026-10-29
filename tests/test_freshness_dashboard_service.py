import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from experiments.freshness.dashboard_service import CONTROL_HEADER, CONTROL_VALUE, server
from experiments.freshness.dashboard_workload import DashboardWorkload


class DashboardServiceTests(unittest.TestCase):
    def setUp(self):
        self.workload = DashboardWorkload()
        self.server = server(0, self.workload)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, path, value=None, controller=False, headers=None):
        request_headers = dict(headers or {})
        data = None
        if value is not None:
            data = json.dumps(value).encode()
            request_headers['Content-Type'] = 'application/json'
        if controller:
            request_headers[CONTROL_HEADER] = CONTROL_VALUE
        request = Request(self.base + path, data=data, headers=request_headers)
        with urlopen(request, timeout=5) as response:
            return response.status, dict(response.headers), json.loads(response.read() or b'null')

    @staticmethod
    def query(resource, filters=None, sort=None, item_range=None):
        return f'/api/{resource}?' + urlencode({
            'filter': json.dumps(filters or {}),
            'sort': json.dumps(sort or ['id', 'ASC']),
            'range': json.dumps(item_range or [0, 99]),
        })

    def test_list_response_has_react_admin_and_oracle_headers(self):
        status, headers, records = self.request(self.query(
            'orders', {'status': 'ordered'}, ['date', 'DESC'], [0, 2],
        ))
        self.assertEqual(status, 200)
        self.assertEqual([record['id'] for record in records], [3, 6, 9])
        self.assertEqual(headers['Content-Range'], 'orders 0-2/4')
        self.assertEqual(headers['X-Origin-Revision'], '0')
        self.assertIn('ETag', headers)
        self.assertIn('X-Content-SHA256', headers)

    def test_cors_exposes_required_headers(self):
        _, headers, _ = self.request(
            self.query('reviews'), headers={'Origin': 'http://127.0.0.1:3110'},
        )
        self.assertEqual(headers['Access-Control-Allow-Origin'], 'http://127.0.0.1:3110')
        self.assertIn('Content-Range', headers['Access-Control-Expose-Headers'])

    def test_validator_returns_304(self):
        path = self.query('reviews', {'status': 'pending'})
        _, headers, _ = self.request(path)
        request = Request(self.base + path, headers={'If-None-Match': headers['ETag']})
        try:
            urlopen(request, timeout=5)
        except HTTPError as error:
            self.assertEqual(error.code, 304)
            self.assertEqual(error.headers['X-Origin-Revision'], '0')
        else:
            self.fail('expected 304 response')

    def test_controls_require_header_and_return_revisioned_oracle(self):
        with self.assertRaises(HTTPError) as denied:
            self.request('/control/reset', {'seed': 0})
        self.assertEqual(denied.exception.code, 403)

        _, _, committed = self.request('/control/commit', {
            'resource': 'orders', 'operation': 'update', 'id': 1,
            'changes': {'total': 999}, 'at_ms': 1,
        }, controller=True)
        self.assertEqual(committed['revision'], 1)
        _, _, oracle = self.request('/control/oracle', {'revision': 1}, controller=True)
        self.assertEqual(oracle['decision_revision'], 1)
        self.assertIn('revenue', oracle['content'])


if __name__ == '__main__':
    unittest.main()
