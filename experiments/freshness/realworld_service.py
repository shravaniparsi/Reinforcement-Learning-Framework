"""Loopback origin service for the prospective mutable RealWorld workload."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Type
from urllib.parse import urlsplit

from .realworld_workload import ALLOWED_TAGS, RealWorldFeedWorkload


CONTROL_HEADER = 'X-Freshness-Study-Control'
CONTROL_VALUE = 'local-controller'
MAX_BODY_BYTES = 1024 * 1024


def handler_for(workload: RealWorldFeedWorkload) -> Type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:
            pass

        def _json(self, status: int, value, headers=None) -> None:
            payload = json.dumps(value, separators=(',', ':'), allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(payload)))
            for name, header_value in (headers or {}).items():
                self.send_header(name, str(header_value))
            self.end_headers()
            self.wfile.write(payload)

        def _authorized(self) -> bool:
            return self.headers.get(CONTROL_HEADER) == CONTROL_VALUE and not self.headers.get('Origin')

        def _read_json(self):
            try:
                length = int(self.headers.get('Content-Length', '0'))
            except ValueError as error:
                raise ValueError('invalid Content-Length') from error
            if not 0 < length <= MAX_BODY_BYTES:
                raise ValueError('request body size is outside declared bounds')
            try:
                value = json.loads(self.rfile.read(length))
            except json.JSONDecodeError as error:
                raise ValueError('request body must be valid JSON') from error
            if not isinstance(value, dict):
                raise ValueError('request body must be a JSON object')
            return value

        def do_GET(self) -> None:
            parsed = urlsplit(self.path)
            try:
                if parsed.path == '/api/tags':
                    self._json(200, {'tags': list(ALLOWED_TAGS)})
                    return
                if parsed.path != '/api/articles':
                    self._json(404, {'error': 'not found'})
                    return
                result = workload.read(parsed.query, validator=self.headers.get('If-None-Match'))
                headers = {
                    'ETag': result.validator,
                    'X-Origin-Revision': result.decision_revision,
                    'X-Content-SHA256': result.content_sha256,
                }
                if result.not_modified:
                    self.send_response(304)
                    self.send_header('Cache-Control', 'no-store')
                    for name, value in headers.items():
                        self.send_header(name, str(value))
                    self.end_headers()
                    return
                self._json(200, result.content, headers=headers)
            except (KeyError, ValueError) as error:
                self._json(400, {'error': str(error)})

        def do_POST(self) -> None:
            if not self._authorized():
                self._json(403, {'error': 'local study controller required'})
                return
            try:
                value = self._read_json()
                if self.path == '/control/reset':
                    seed = value.get('seed')
                    workload.reset(seed)
                    self._json(200, {'status': 'reset', 'seed': seed})
                elif self.path == '/control/commit':
                    at_ms = value.pop('at_ms', None)
                    record = workload.commit(value, at_ms=at_ms)
                    self._json(200, asdict(record))
                else:
                    self._json(404, {'error': 'not found'})
            except (KeyError, TypeError, ValueError) as error:
                self._json(400, {'error': str(error)})

    return Handler


def server(port: int, workload: RealWorldFeedWorkload) -> ThreadingHTTPServer:
    if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
        raise ValueError('port must be between 0 and 65535')
    return ThreadingHTTPServer(('127.0.0.1', port), handler_for(workload))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=3206)
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()
    origin = RealWorldFeedWorkload()
    origin.reset(args.seed)
    httpd = server(args.port, origin)
    print(f'Mutable RealWorld origin: http://127.0.0.1:{httpd.server_port}', flush=True)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
        origin.close()
