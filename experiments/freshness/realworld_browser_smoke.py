"""Semantic W2 browser gate; this script does not collect performance data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, List
from urllib.error import URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_APP = ROOT / 'experiments/vendor/svelte-realworld-freshness'
UPSTREAM_COMMIT = 'df796708040f5200ec572b28ab7f88ecee5794dd'
CONTROL_HEADER = 'X-Freshness-Study-Control'
CONTROL_VALUE = 'local-controller'


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob('*') if item.is_file()):
        relative = path.relative_to(root).as_posix().encode('utf-8')
        digest.update(len(relative).to_bytes(4, 'big'))
        digest.update(relative)
        digest.update(bytes.fromhex(sha256(path)))
    return digest.hexdigest()


def json_request(url: str, value: Dict | None = None, controller: bool = False) -> Dict:
    headers = {}
    data = None
    if value is not None:
        data = json.dumps(value, separators=(',', ':')).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    if controller:
        headers[CONTROL_HEADER] = CONTROL_VALUE
    request = Request(url, data=data, headers=headers, method='POST' if data is not None else 'GET')
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read())


def wait_ready(url: str, process: subprocess.Popen, timeout_s: float = 20.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f'process exited before readiness: {process.args}')
        try:
            with urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return
        except URLError:
            time.sleep(0.1)
    raise TimeoutError(f'timed out waiting for {url}')


@contextmanager
def services(app_dir: Path, node: Path, origin_port: int, app_port: int, output: Path) -> Iterator[None]:
    origin_log = (output / 'origin.log').open('w')
    app_log = (output / 'app.log').open('w')
    origin_environment = os.environ.copy()
    origin_environment['PYTHONPATH'] = str(ROOT / 'experiments')
    origin = subprocess.Popen(
        [sys.executable, '-m', 'freshness.realworld_service', '--port', str(origin_port), '--seed', '0'],
        cwd=ROOT / 'experiments', env=origin_environment, stdout=origin_log, stderr=subprocess.STDOUT,
        text=True,
    )
    app_environment = os.environ.copy()
    app_environment.update({
        'HOST': '127.0.0.1',
        'PORT': str(app_port),
        'ORIGIN': f'http://127.0.0.1:{app_port}',
    })
    app = subprocess.Popen(
        [str(node), 'build-freshness/index.js'], cwd=app_dir, env=app_environment,
        stdout=app_log, stderr=subprocess.STDOUT, text=True,
    )
    try:
        wait_ready(f'http://127.0.0.1:{origin_port}/api/tags', origin)
        wait_ready(f'http://127.0.0.1:{app_port}/', app)
        yield
    finally:
        for process in (app, origin):
            if process.poll() is None:
                process.terminate()
        for process in (app, origin):
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        origin_log.close()
        app_log.close()


def origin_titles(origin_base: str, query: Dict[str, str | int]) -> List[str]:
    payload = json_request(f'{origin_base}/api/articles?{urlencode(query)}')
    return [article['title'] for article in payload['articles']]


def page_titles(page: Page) -> List[str]:
    page.wait_for_function("document.documentElement.dataset.feedReady === 'true'")
    return page.locator('.article-preview h1').all_text_contents()


def verify_view(
    page: Page, app_base: str, origin_base: str, query: Dict[str, str | int], label: str,
) -> Dict:
    expected = origin_titles(origin_base, query)
    browser_query = dict(query)
    offset = int(browser_query.pop('offset', 0))
    limit = int(browser_query.pop('limit', 10))
    if limit != 10 or offset % 10:
        raise ValueError('browser smoke supports the application page size of 10')
    browser_query['page'] = offset // 10 + 1
    url = f'{app_base}/?{urlencode(browser_query)}'
    with urlopen(url, timeout=10) as response:
        html = response.read().decode('utf-8')
    if expected and f'<h1>{expected[0]}</h1>' not in html:
        raise AssertionError(f'{label}: first oracle title absent from SSR HTML')
    response = page.goto(url, wait_until='networkidle')
    if response is None or response.status != 200:
        raise AssertionError(f'{label}: browser navigation failed')
    observed = page_titles(page)
    if observed != expected:
        raise AssertionError(f'{label}: browser titles differ from the origin: {observed!r} != {expected!r}')
    return {
        'label': label,
        'query': query,
        'article_count': len(observed),
        'ssr_first_title_verified': bool(expected),
        'hydrated_content_matches_origin': True,
    }


def commit(origin_base: str, mutation: Dict) -> Dict:
    return json_request(f'{origin_base}/control/commit', mutation, controller=True)


def run(args: argparse.Namespace) -> Dict:
    app_dir = args.app_dir.resolve()
    build_dir = app_dir / 'build-freshness'
    if not (build_dir / 'index.js').is_file():
        raise FileNotFoundError('clean W2 build missing: build-freshness/index.js')
    if args.origin_port != 3206:
        raise ValueError('freshness-api.patch pins the controlled origin to port 3206')
    args.output.mkdir(parents=True, exist_ok=False)

    origin_base = f'http://127.0.0.1:{args.origin_port}'
    app_base = f'http://127.0.0.1:{args.app_port}'
    checks = []
    browser_errors: List[str] = []
    external_requests: List[str] = []

    with services(app_dir, args.node, args.origin_port, args.app_port, args.output):
        json_request(f'{origin_base}/control/reset', {'seed': 0}, controller=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='chrome', headless=True)
            try:
                context = browser.new_context(viewport={'width': 1365, 'height': 900}, service_workers='block')

                def restrict(route) -> None:
                    hostname = urlparse(route.request.url).hostname
                    if hostname not in {'127.0.0.1', 'localhost', None}:
                        external_requests.append(route.request.url)
                        route.abort()
                    else:
                        route.continue_()

                context.route('**/*', restrict)
                page = context.new_page()
                page.on('pageerror', lambda error: browser_errors.append(str(error)))
                page.on(
                    'requestfailed',
                    lambda request: browser_errors.append(f'{request.url}: {request.failure}'),
                )
                page.on(
                    'response',
                    lambda response: browser_errors.append(f'HTTP {response.status}: {response.url}')
                    if response.status >= 400 else None,
                )

                feed = {'limit': 10, 'offset': 0}
                rendering = {'tag': 'rendering', 'limit': 10, 'offset': 0}
                accessibility = {'tag': 'accessibility', 'limit': 10, 'offset': 0}
                checks.append(verify_view(page, app_base, origin_base, feed, 'initial-feed'))
                checks.append(verify_view(page, app_base, origin_base, rendering, 'initial-rendering-tag'))

                update = commit(origin_base, {
                    'operation': 'update', 'slug': 'independent-note-29',
                    'changes': {'title': 'Updated independent note 29'}, 'at_ms': 1000,
                })
                checks.append(verify_view(page, app_base, origin_base, feed, 'after-title-update'))

                tag_change = commit(origin_base, {
                    'operation': 'update', 'slug': 'independent-note-28',
                    'changes': {'tagList': ['accessibility']}, 'at_ms': 2000,
                })
                checks.append(verify_view(page, app_base, origin_base, rendering, 'after-tag-removal'))
                checks.append(verify_view(page, app_base, origin_base, accessibility, 'after-tag-addition'))

                create = commit(origin_base, {
                    'operation': 'create',
                    'article': {
                        'slug': 'controlled-new-note', 'title': 'Controlled new note',
                        'description': 'Created by the local study controller.',
                        'body': 'Synthetic local article.', 'tagList': ['rendering'],
                    },
                    'at_ms': 3000,
                })
                checks.append(verify_view(page, app_base, origin_base, feed, 'after-create'))
                checks.append(verify_view(page, app_base, origin_base, rendering, 'after-create-rendering'))

                delete = commit(origin_base, {
                    'operation': 'delete', 'slug': 'controlled-new-note', 'at_ms': 4000,
                })
                checks.append(verify_view(page, app_base, origin_base, feed, 'after-delete'))
                checks.append(verify_view(page, app_base, origin_base, rendering, 'after-delete-rendering'))
                page.screenshot(path=str(args.output / 'w2-browser-smoke.png'), full_page=False)

                if external_requests or browser_errors:
                    raise AssertionError(
                        f'external requests: {external_requests}; browser errors: {browser_errors}'
                    )
                result = {
                    'purpose': 'semantic_W2_browser_gate_only',
                    'performance_measurements': False,
                    'upstream_url': 'https://github.com/sveltejs/realworld',
                    'upstream_commit': UPSTREAM_COMMIT,
                    'browser_version': browser.version,
                    'checks': checks,
                    'commit_revisions': [update['revision'], tag_change['revision'], create['revision'], delete['revision']],
                    'external_requests': external_requests,
                    'browser_errors': browser_errors,
                    'build_tree_sha256': tree_sha256(build_dir),
                    'lockfile_sha256': sha256(app_dir / 'pnpm-lock.yaml'),
                    'patch_sha256': {
                        'production-variants.patch': sha256(ROOT / 'experiments/external/svelte-realworld/production-variants.patch'),
                        'freshness-api.patch': sha256(ROOT / 'experiments/external/svelte-realworld/freshness-api.patch'),
                    },
                }
                (args.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
                return result
            finally:
                browser.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-dir', type=Path, default=DEFAULT_APP)
    parser.add_argument(
        '--node', type=Path,
        default=Path('/Users/shravaniparsi/.nvm/versions/node/v20.19.6/bin/node'),
    )
    parser.add_argument('--origin-port', type=int, default=3206)
    parser.add_argument('--app-port', type=int, default=3108)
    parser.add_argument(
        '--output', type=Path,
        default=ROOT / 'data/engineering/freshness-w2-browser-smoke-v1',
    )
    args = parser.parse_args()
    result = run(args)
    print(f"{len(result['checks'])} semantic browser checks passed: {args.output}")


if __name__ == '__main__':
    main()
