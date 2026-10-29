"""Semantic W3 browser gate; this script records no performance observations."""

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
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_APP = ROOT / 'experiments/vendor/react-admin/examples/demo'
UPSTREAM_COMMIT = '0c33d9c3c27cc4bf97e11f56080c5bfe182f2f2a'
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
        relative = path.relative_to(root).as_posix().encode()
        digest.update(len(relative).to_bytes(4, 'big'))
        digest.update(relative)
        digest.update(bytes.fromhex(sha256(path)))
    return digest.hexdigest()


def json_request(url: str, value: Dict | None = None) -> Dict:
    headers = {}
    data = None
    if value is not None:
        data = json.dumps(value, separators=(',', ':')).encode()
        headers.update({'Content-Type': 'application/json', CONTROL_HEADER: CONTROL_VALUE})
    request = Request(url, data=data, headers=headers, method='POST' if data is not None else 'GET')
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read())


def wait_ready(url: str, process: subprocess.Popen, timeout_s: float = 30.0) -> None:
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
        [sys.executable, '-m', 'freshness.dashboard_service', '--port', str(origin_port), '--seed', '0'],
        cwd=ROOT / 'experiments', env=origin_environment, stdout=origin_log, stderr=subprocess.STDOUT,
        text=True,
    )
    app = subprocess.Popen(
        [
            str(node), str(app_dir / 'node_modules/vite/bin/vite.js'), 'preview',
            '--host', '127.0.0.1', '--port', str(app_port), '--strictPort',
        ],
        cwd=app_dir, stdout=app_log, stderr=subprocess.STDOUT, text=True,
    )
    try:
        wait_ready(f'http://127.0.0.1:{origin_port}/api/orders', origin)
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


def card(page: Page, title: str):
    result = page.locator('.MuiCard-root').filter(has_text=title).first
    result.wait_for(state='visible')
    return result


def verify_dashboard(page: Page, origin_base: str, revision: int, label: str) -> Dict:
    oracle = json_request(f'{origin_base}/control/oracle', {'revision': revision})['content']
    page.reload(wait_until='networkidle')
    card(page, 'Monthly Revenue')
    page.wait_for_function(
        "() => [...document.querySelectorAll('.MuiCard-root')].some(n => "
        "n.textContent.includes('Pending Reviews') && n.querySelectorAll('.MuiListItem-root').length > 0)"
    )

    expected_revenue = page.evaluate(
        "value => new Intl.NumberFormat(undefined, {style: 'currency', currency: 'USD', "
        "minimumFractionDigits: 0, maximumFractionDigits: 0}).format(value)",
        oracle['revenue'],
    )
    observed_revenue = card(page, 'Monthly Revenue').locator('h2').first.text_content().strip()
    observed_orders = card(page, 'New Orders').locator('h2').first.text_content().strip()
    observed_reviews = card(page, 'Pending Reviews').locator('h2').first.text_content().strip()
    observed_customers = card(page, 'New Customers').locator('h2').first.text_content().strip()
    scalar_expected = {
        'revenue': expected_revenue,
        'new_orders': str(oracle['new_order_count']),
        'pending_reviews': str(oracle['pending_review_count']),
        'new_customers': str(oracle['new_customer_count']),
    }
    scalar_observed = {
        'revenue': observed_revenue,
        'new_orders': observed_orders,
        'pending_reviews': observed_reviews,
        'new_customers': observed_customers,
    }
    if scalar_observed != scalar_expected:
        raise AssertionError(f'{label}: scalar dashboard mismatch: {scalar_observed} != {scalar_expected}')

    pending_card = card(page, 'Pending Orders')
    for order in oracle['pending_orders']:
        customer = oracle['referenced_customers'][str(order['customer_id'])]
        name = f"{customer['first_name']} {customer['last_name']}"
        item = pending_card.locator(f'[data-study-order-id="{order["id"]}"]')
        item.wait_for(state='visible')
        customer_name = item.locator('[data-study-customer-name]').get_attribute(
            'data-study-customer-name'
        )
        if customer_name != name or f"{order['total']}$" not in item.inner_text():
            raise AssertionError(f'{label}: pending order {order["id"]} differs from oracle')

    review_card = card(page, 'Pending Reviews')
    for review in oracle['pending_reviews']:
        customer = oracle['referenced_customers'][str(review['customer_id'])]
        name = f"{customer['first_name']} {customer['last_name']}"
        item = review_card.locator(f'[data-study-review-id="{review["id"]}"]')
        item.wait_for(state='visible')
        customer_name = item.locator('[data-study-customer-name]').get_attribute(
            'data-study-customer-name'
        )
        if review['comment'] not in item.inner_text() or customer_name != name:
            raise AssertionError(f'{label}: pending review {review["id"]} differs from oracle')

    customer_text = card(page, 'New Customers').inner_text()
    for customer in oracle['new_customers']:
        name = f"{customer['first_name']} {customer['last_name']}"
        if name not in customer_text:
            raise AssertionError(f'{label}: new customer {customer["id"]} differs from oracle')

    return {
        'label': label,
        'revision': revision,
        'scalar_fields': scalar_observed,
        'pending_order_ids': [record['id'] for record in oracle['pending_orders']],
        'pending_review_ids': [record['id'] for record in oracle['pending_reviews']],
        'new_customer_ids': [record['id'] for record in oracle['new_customers']],
        'browser_matches_single_revision_oracle': True,
    }


def commit(origin_base: str, mutation: Dict) -> Dict:
    return json_request(f'{origin_base}/control/commit', mutation)


def run(args: argparse.Namespace) -> Dict:
    app_dir = args.app_dir.resolve()
    if not (app_dir / 'dist/index.html').is_file():
        raise FileNotFoundError('adapted W3 production build missing: dist/index.html')
    if args.origin_port != 3210 or args.app_port != 3110:
        raise ValueError('the recorded W3 adaptation pins origin 3210 and app 3110')
    args.output.mkdir(parents=True, exist_ok=False)
    origin_base = f'http://127.0.0.1:{args.origin_port}'
    app_base = f'http://127.0.0.1:{args.app_port}'
    checks = []
    browser_errors: List[str] = []
    external_requests: List[str] = []

    with services(app_dir, args.node, args.origin_port, args.app_port, args.output):
        json_request(f'{origin_base}/control/reset', {'seed': 0})
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='chrome', headless=True)
            try:
                context = browser.new_context(viewport={'width': 1600, 'height': 1000}, service_workers='block')
                context.add_init_script("localStorage.setItem('username', 'study-user')")

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
                response = page.goto(app_base + '/', wait_until='networkidle')
                if response is None or response.status != 200:
                    raise AssertionError('W3 navigation failed')
                checks.append(verify_dashboard(page, origin_base, 0, 'initial-dashboard'))

                order_update = commit(origin_base, {
                    'resource': 'orders', 'operation': 'update', 'id': 1,
                    'changes': {'total': 999, 'status': 'ordered'}, 'at_ms': 1000,
                })
                checks.append(verify_dashboard(page, origin_base, 1, 'after-order-update'))

                review_update = commit(origin_base, {
                    'resource': 'reviews', 'operation': 'update', 'id': 1,
                    'changes': {'status': 'accepted'}, 'at_ms': 2000,
                })
                checks.append(verify_dashboard(page, origin_base, 2, 'after-review-update'))

                customer_update = commit(origin_base, {
                    'resource': 'customers', 'operation': 'update', 'id': 3,
                    'changes': {'first_name': 'UpdatedCustomer3'}, 'at_ms': 3000,
                })
                checks.append(verify_dashboard(page, origin_base, 3, 'after-customer-update'))

                customer_create = commit(origin_base, {
                    'resource': 'customers', 'operation': 'create',
                    'record': {
                        'id': 9, 'first_name': 'Created', 'last_name': 'Customer',
                        'avatar': 'data:image/svg+xml,fixture',
                        'first_seen': '2026-10-29T10:00:00.000Z', 'has_ordered': True,
                    },
                    'at_ms': 4000,
                })
                checks.append(verify_dashboard(page, origin_base, 4, 'after-customer-create'))
                page.screenshot(path=str(args.output / 'w3-dashboard-smoke.png'), full_page=True)

                if external_requests or browser_errors:
                    raise AssertionError(
                        f'external requests: {external_requests}; browser errors: {browser_errors}'
                    )
                result = {
                    'purpose': 'semantic_W3_browser_gate_only',
                    'performance_measurements': False,
                    'upstream_url': 'https://github.com/marmelab/react-admin',
                    'upstream_commit': UPSTREAM_COMMIT,
                    'browser_version': browser.version,
                    'checks': checks,
                    'commit_revisions': [
                        order_update['revision'], review_update['revision'],
                        customer_update['revision'], customer_create['revision'],
                    ],
                    'external_requests': external_requests,
                    'browser_errors': browser_errors,
                    'build_tree_sha256': tree_sha256(app_dir / 'dist'),
                    'lockfile_sha256': sha256(app_dir / 'pnpm-lock.yaml'),
                    'adaptation_patch_sha256': sha256(
                        ROOT / 'experiments/external/react-admin/controlled-backend.patch'
                    ),
                    'upstream_license_sha256': sha256(
                        ROOT / 'experiments/external/react-admin/LICENSE.upstream'
                    ),
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
    parser.add_argument('--origin-port', type=int, default=3210)
    parser.add_argument('--app-port', type=int, default=3110)
    parser.add_argument(
        '--output', type=Path,
        default=ROOT / 'data/engineering/freshness-w3-browser-smoke-v4',
    )
    args = parser.parse_args()
    result = run(args)
    print(f"{len(result['checks'])} semantic dashboard checks passed: {args.output}")


if __name__ == '__main__':
    main()
