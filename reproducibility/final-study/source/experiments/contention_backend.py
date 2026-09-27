"""Local read-only article service: actual SQLite query work, no imposed sleeps."""
import argparse
import json
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

TAGS = ('rendering', 'accessibility')


class ArticleStore:
    def __init__(self, size=50000):
        if not 40 <= size <= 100000:
            raise ValueError('Fixture size outside permitted range')
        self.size = size
        self.lock = threading.Lock()
        self.db = sqlite3.connect(':memory:', check_same_thread=False)
        self.db.execute('CREATE TABLE articles (id INTEGER PRIMARY KEY, title TEXT, body TEXT, tag TEXT)')
        self.db.executemany('INSERT INTO articles VALUES (?, ?, ?, ?)', (
            (i, f'Engineering note {i:05d}',
             (f'A practical note about {TAGS[i % 2]} and careful measurement. ' * 16), TAGS[i % 2])
            for i in range(size)))
        self.db.execute('CREATE INDEX article_tag_id ON articles(tag, id)')
        self.db.commit()
        self.requests = 0

    def articles(self, tag='rendering', offset=0, query_mode='scan'):
        if tag not in TAGS or not isinstance(offset, int) or not 0 <= offset <= self.size - 20:
            raise ValueError('Invalid tag or offset')
        if query_mode not in {'scan', 'indexed'}:
            raise ValueError('Invalid query mode')
        arrived = time.perf_counter()
        with self.lock:
            acquired = time.perf_counter()
            cpu_start = time.thread_time()
            # Equivalent only for this fixture: body topic and normalized tag agree.
            predicate = '%' + tag + '%' if query_mode == 'scan' else tag
            where = 'lower(body) LIKE ?' if query_mode == 'scan' else 'tag = ?'
            count = self.db.execute('SELECT count(*) FROM articles WHERE ' + where, (predicate,)).fetchone()[0]
            records = self.db.execute(
                'SELECT id, title FROM articles WHERE ' + where + ' ORDER BY id DESC LIMIT 20 OFFSET ?',
                (predicate, offset)).fetchall()
            self.requests += 1
            request_id = self.requests
            cpu_seconds = time.thread_time() - cpu_start
            finished = time.perf_counter()
        return {'articles': [
            {'slug': f'note-{i}', 'title': title, 'description': f'A practical note about {tag}.',
             'tagList': [tag]} for i, title in records], 'articlesCount': count,
            'backend': {'query_mode': query_mode, 'request_id': request_id, 'queue_ms': (acquired - arrived) * 1000,
                        'query_wall_ms': (finished - acquired) * 1000,
                        'query_thread_cpu_seconds': cpu_seconds},
            'fixture': {'rows': self.size, 'tag': tag, 'offset': offset}}

    def plans(self):
        with self.lock:
            return {name: [list(row) for row in self.db.execute('EXPLAIN QUERY PLAN ' + sql, ('rendering',))]
                    for name, sql in {
                        'count': 'SELECT count(*) FROM articles WHERE tag = ?',
                        'page': 'SELECT id, title FROM articles WHERE tag = ? ORDER BY id DESC LIMIT 20'
                    }.items()}

    def close(self):
        self.db.close()


def make_server(port, store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            parsed = urlparse(self.path)
            status = 200
            try:
                if parsed.path == '/articles':
                    args = parse_qs(parsed.query)
                    value = store.articles(args.get('tag', ['rendering'])[0], int(args.get('offset', ['0'])[0]), args.get('query_mode', ['scan'])[0])
                elif parsed.path == '/health':
                    value = {'rows': store.size, 'sqlite_version': sqlite3.sqlite_version,
                             'query_model': 'serialized in-memory SQLite', 'query_modes': ['scan', 'indexed'],
                             'indexed_plans': store.plans(), 'imposed_delay_ms': 0}
                else:
                    status, value = 404, {'error': 'Not found'}
            except ValueError as error:
                status, value = 400, {'error': str(error)}
            payload = json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=3203)
    args = parser.parse_args()
    store = ArticleStore()
    print(f'Article service ready: http://127.0.0.1:{args.port}', flush=True)
    make_server(args.port, store).serve_forever()
