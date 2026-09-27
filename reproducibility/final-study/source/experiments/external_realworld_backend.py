"""Read-only local API subset for an upstream RealWorld reproducibility smoke check."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ARTICLES = [
    {'slug': f'independent-note-{i}', 'title': f'Independent note {i:02d}',
     'description': f'Local reproducibility fixture {i:02d}.', 'body': 'Synthetic local article.',
     'tagList': ['rendering' if i % 2 == 0 else 'accessibility'],
     'createdAt': '2026-01-01T00:00:00.000Z', 'updatedAt': '2026-01-01T00:00:00.000Z',
     'favorited': False, 'favoritesCount': 0,
     'author': {'username': 'fixture-author', 'bio': 'Local fixture', 'image':
                'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="32" height="32"%3E%3Crect width="32" height="32" fill="%23888"/%3E%3C/svg%3E',
                'following': False}}
    for i in range(29, -1, -1)]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        status = 200
        try:
            if parsed.path == '/api/tags':
                value = {'tags': ['rendering', 'accessibility']}
            elif parsed.path == '/api/articles':
                args = parse_qs(parsed.query)
                tag = args.get('tag', [None])[0]
                limit, offset = int(args.get('limit', ['10'])[0]), int(args.get('offset', ['0'])[0])
                if tag not in {None, 'rendering', 'accessibility'} or not 1 <= limit <= 20 or not 0 <= offset <= 30:
                    raise ValueError('Invalid fixture query')
                items = [a for a in ARTICLES if tag is None or tag in a['tagList']]
                value = {'articles': items[offset:offset + limit], 'articlesCount': len(items)}
            else:
                status, value = 404, {'error': 'Endpoint outside smoke-check scope'}
        except ValueError as error:
            status, value = 400, {'error': str(error)}
        payload = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == '__main__':
    print('External-app fixture API: http://127.0.0.1:3205', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 3205), Handler).serve_forever()
