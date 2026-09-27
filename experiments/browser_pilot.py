"""Measure the production Next.js fixture. Pilot data, not RL evaluation."""
import argparse
import hashlib
import json
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/env'))
from provenance import source_metadata, file_hash, run_directory

PROFILES = {
    'local-desktop': {'latency_ms': 0, 'mbps': 100, 'cpu_rate': 1},
    'emulated-constrained': {'latency_ms': 80, 'mbps': 5, 'cpu_rate': 4},
}
STRATEGIES = ['csr', 'ssr', 'ssg']

OBSERVER = """(() => {
  let scheduled = false;
  const checkContent = () => {
    const products = document.querySelectorAll('article[data-product-id]');
    if (scheduled || products.length !== 24) return;
    scheduled = true;
    performance.mark('catalog-dom-complete');
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const rect = products[0].getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0 && rect.top < innerHeight) {
        performance.mark('catalog-visible-opportunity');
      }
    }));
  };
  new MutationObserver(checkContent).observe(document, {childList: true, subtree: true});
  window.__pilotLcp = [];
  window.__pilotObserver = new PerformanceObserver(list => {
    for (const e of list.getEntries()) window.__pilotLcp.push({
      startTime: e.startTime, size: e.size,
      element: e.element?.tagName || null,
      text: e.element?.textContent?.slice(0, 100) || null
    });
  });
  window.__pilotObserver.observe({type: 'largest-contentful-paint', buffered: true});
})();"""


def read_json(url):
    with urlopen(url, timeout=10) as response:
        return json.load(response)


def inspect_delivery(base_url):
    checks = {}
    for strategy in STRATEGIES:
        with urlopen(f'{base_url}/{strategy}', timeout=10) as response:
            html = response.read().decode()
        # Match actual markup, not serialized React data in script tags.
        has_products = '<article data-product-id="product-1"' in html
        checks[strategy] = {'products_in_initial_html': has_products}
        if has_products != (strategy != 'csr'):
            raise AssertionError(f'{strategy}: initial HTML delivery contract failed')
    return checks


def run_trial(browser, base_url, fixture, trial, output):
    profile = PROFILES[trial['profile']]
    context = browser.new_context(viewport={'width': 1365, 'height': 900},
                                  device_scale_factor=1, service_workers='block')
    errors, failed_requests = [], []
    try:
        if trial.get('identity'):
            context.add_cookies([{'name': 'fixture-user', 'value': trial['identity'], 'url': base_url}])
        context.add_init_script(OBSERVER)
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('requestfailed', lambda request: failed_requests.append({
            'url': request.url, 'failure': request.failure}))
        page.on('response', lambda response: errors.append(f'HTTP {response.status}: {response.url}')
                if response.status >= 400 else None)
        cdp = context.new_cdp_session(page)
        cdp.send('Network.enable')
        cdp.send('Network.emulateNetworkConditions', {
            'offline': False, 'latency': profile['latency_ms'],
            'downloadThroughput': profile['mbps'] * 1_000_000 / 8,
            'uploadThroughput': profile['mbps'] * 1_000_000 / 8,
        })
        cdp.send('Emulation.setCPUThrottlingRate', {'rate': profile['cpu_rate']})
        url = base_url + trial.get('path', f"/{trial['strategy']}")
        if trial['cache'] == 'warm-browser':
            page.goto(url, wait_until='load')
            page.wait_for_selector('main[data-ready="true"]')
            page.wait_for_timeout(250)
        cpu_before = read_json(base_url + '/api/telemetry') if trial.get('measure_process_cpu') else None
        response = page.goto(url, wait_until='load', timeout=30000)
        if response.status != 200:
            raise AssertionError(f'Navigation HTTP {response.status}')
        page.wait_for_selector('main[data-ready="true"]', timeout=30000)
        cpu_after = read_json(base_url + '/api/telemetry') if cpu_before else None
        page.wait_for_timeout(1000)  # identical, explicit LCP observation window
        observed = page.locator('article').evaluate_all("""nodes => nodes.map(n => ({
            id: n.dataset.productId, name: n.querySelector('h2').textContent,
            price: n.querySelector('[data-price]').textContent
        }))""")
        expected = [{'id': p['id'], 'name': p['name'],
                     'price': f"{p['priceCents'] / 100:.2f}"} for p in fixture['products']]
        if observed != expected:
            raise AssertionError('Product content differs from fixture')
        if page.locator('main').get_attribute('data-version') != fixture['version']:
            raise AssertionError('Fixture version mismatch')
        metrics = page.evaluate("""() => {
            const nav = performance.getEntriesByType('navigation')[0];
            const resources = performance.getEntriesByType('resource');
            const ready = performance.getEntriesByName('catalog-interactive')[0];
            const lcp = window.__pilotLcp.at(-1) || null;
            return {
                ttfb_ms: nav.responseStart - nav.startTime,
                request_ttfb_ms: nav.responseStart - nav.requestStart,
                dom_content_loaded_ms: nav.domContentLoadedEventEnd,
                load_event_ms: nav.loadEventEnd,
                catalog_interactive_ms: ready?.startTime ?? null,
                catalog_dom_complete_ms: performance.getEntriesByName('catalog-dom-complete')[0]?.startTime ?? null,
                catalog_visible_opportunity_ms: performance.getEntriesByName('catalog-visible-opportunity')[0]?.startTime ?? null,
                lcp_ms: lcp?.startTime ?? null, lcp_candidate: lcp,
                resource_timing_transfer_bytes: nav.transferSize + resources.reduce((s, r) => s + r.transferSize, 0),
                resources: resources.map(r => ({name: r.name, transferSize: r.transferSize,
                    encodedBodySize: r.encodedBodySize, initiatorType: r.initiatorType})),
                server_cpu_seconds: null
            };
        }""")
        if metrics['lcp_ms'] is None or metrics['catalog_interactive_ms'] is None:
            raise AssertionError('Required browser timing is missing')
        if metrics['catalog_visible_opportunity_ms'] is None:
            raise AssertionError('Catalog visibility opportunity marker missing')
        if cpu_before:
            if cpu_before['pid'] != cpu_after['pid']:
                raise AssertionError('Server PID changed during CPU measurement')
            metrics['server_process_cpu_window_seconds'] = sum(
                cpu_after['cpu'][key] - cpu_before['cpu'][key] for key in ['user', 'system']) / 1e6
            metrics['server_process_cpu_window_wall_seconds'] = cpu_after['uptime'] - cpu_before['uptime']
        # Separate custom interaction measurement; this is not field INP.
        page.evaluate("""() => {
            window.__pilotClickStart = null;
            document.querySelector('article button').addEventListener('click', () => {
                window.__pilotClickStart = performance.now();
            }, {capture: true, once: true});
        }""")
        page.locator('article button').first.click()
        page.wait_for_function("document.querySelector('#cart-count').textContent === '1'")
        metrics['scripted_click_to_two_frames_ms'] = page.evaluate("""() => new Promise(resolve => {
            requestAnimationFrame(() => requestAnimationFrame(() => resolve(performance.now() - window.__pilotClickStart)));
        })""")
        if page.locator('#cart-total').inner_text() != f"{fixture['products'][0]['priceCents'] / 100:.2f}":
            raise AssertionError('Cart total is incorrect')
        if errors or failed_requests:
            raise AssertionError(f'Browser errors: {errors}; request failures: {failed_requests}')
        if trial['index'] == 0:
            page.screenshot(path=str(output / 'pilot-check.png'), full_page=False)
        return {**trial, 'status': 'ok', 'correctness': True,
                'dom_sha256': hashlib.sha256(json.dumps(observed, sort_keys=True).encode()).hexdigest(),
                'metrics': metrics, 'errors': errors, 'failed_requests': failed_requests}
    finally:
        context.close()


def summarize(rows, output):
    lines = ['# Browser pilot — engineering validation only', '',
             'Single local catalog, 24 products, one cart interaction. No RL comparison or publication claim.',
             'Descriptive medians only. Cold/warm refer to browser cache; server is already warm.', '',
             '| Profile | Browser cache | Strategy | Passed/total | Median LCP (ms) | Median interactive (ms) |',
             '|---|---|---|---|---|---|']
    for profile in PROFILES:
        for cache in ['cold-browser', 'warm-browser']:
            for strategy in STRATEGIES:
                group = [r for r in rows if (r['profile'], r['cache'], r['strategy']) == (profile, cache, strategy)]
                passed = [r for r in group if r['status'] == 'ok']
                lcp = f"{statistics.median(r['metrics']['lcp_ms'] for r in passed):.2f}" if passed else '—'
                ready = f"{statistics.median(r['metrics']['catalog_interactive_ms'] for r in passed):.2f}" if passed else '—'
                lines.append(f'| {profile} | {cache} | {strategy} | {len(passed)}/{len(group)} | {lcp} | {ready} |')
    lines += ['', 'Limitations: emulated CPU/network, one application, small pilot sample, no production users,',
              'no server CPU or build/revalidation cost measurement, no calibrated simulator, no learned-policy evaluation.',
              'The custom click metric includes automation/observation delay and is not INP.',
              'Transfer sizes are browser Resource Timing values, not packet-level wire-byte measurements.']
    (output / 'summary.md').write_text('\n'.join(lines) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:3100')
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--order-seed', type=int, default=20260918)
    parser.add_argument('--output-dir')
    parser.add_argument('--channel', default='chrome', help='Use an installed Chromium channel')
    args = parser.parse_args()
    if urlparse(args.base_url).hostname not in {'127.0.0.1', 'localhost'}:
        parser.error('This pilot only measures the local fixture')
    if args.repetitions < 1:
        parser.error('Positive repetition count required')
    build = ROOT / 'apps/benchmark/.next/BUILD_ID'
    if not build.is_file():
        parser.error('Build the production benchmark first')
    output = Path(args.output_dir or run_directory('browser-pilot'))
    output.mkdir(parents=True, exist_ok=False)
    fixture = read_json(args.base_url + '/api/catalog')
    delivery = inspect_delivery(args.base_url)
    trials = []
    rng = random.Random(args.order_seed)
    for repetition in range(args.repetitions):
        block = [{'repetition': repetition, 'profile': profile, 'cache': cache, 'strategy': strategy}
                 for profile in PROFILES for cache in ['cold-browser', 'warm-browser'] for strategy in STRATEGIES]
        rng.shuffle(block)
        trials.extend(block)
    rows = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.channel, headless=True)
        try:
            source_files = sorted(p for p in (ROOT / 'apps/benchmark').rglob('*')
                                  if p.is_file() and '.next' not in p.parts)
            source_files.append(Path(__file__))
            metadata = {'schema_version': 1, 'purpose': 'engineering_pilot_not_confirmatory',
                        'measurement_kind': 'browser', 'created_utc': datetime.now(timezone.utc).isoformat(),
                        'browser_version': browser.version, 'browser_channel': args.channel,
                        'source': source_metadata(), 'build_id': build.read_text().strip(),
                        'source_sha256': {str(p.relative_to(ROOT)): file_hash(p) for p in source_files},
                        'package_lock_sha256': file_hash(ROOT / 'package-lock.json'),
                        'fixture': fixture, 'delivery_checks': delivery,
                        'profiles': PROFILES, 'order_seed': args.order_seed, 'trials': trials,
                        'cache_protocol': 'fresh browser context per trial; one unmeasured navigation for warm-browser',
                        'server_state': 'warm; initial delivery checks precede measurement',
                        'lcp_window': '1000ms after interactive marker, before first input',
                        'server_cpu_seconds': 'not instrumented in this pilot'}
            (output / 'manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
            with (output / 'measurements.jsonl').open('x') as stream:
                for index, trial in enumerate(trials):
                    trial = {**trial, 'index': index}
                    try:
                        row = run_trial(browser, args.base_url, fixture, trial, output)
                    except Exception as error:
                        row = {**trial, 'status': 'failed', 'error': str(error)}
                    stream.write(json.dumps(row) + '\n'); stream.flush()
                    rows.append(row)
                    print(f"{index + 1}/{len(trials)} {trial['strategy']} {trial['profile']} {trial['cache']}: {row['status']}", flush=True)
        finally:
            browser.close()
    summarize(rows, output)
    print(f'Results: {output}')
    if any(r['status'] != 'ok' for r in rows):
        raise SystemExit('Pilot has failures; inspect raw records before interpreting results')


if __name__ == '__main__':
    main()
