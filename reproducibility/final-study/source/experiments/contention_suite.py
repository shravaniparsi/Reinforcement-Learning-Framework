"""Article-listing rendering under measured SQLite contention; exploratory only."""
import argparse
import hashlib
import json
import random
import shutil
import statistics
import threading
import time
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from browser_pilot import ROOT, PROFILES, read_json
from provenance import file_hash, run_directory, source_metadata

ORIGIN = 'http://127.0.0.1:3203'


def expected_articles(tag, offset, size=50000):
    parity = 0 if tag == 'rendering' else 1
    ids = [i for i in range(size - 1, -1, -1) if i % 2 == parity][offset:offset + 20]
    return [{'slug': f'note-{i}', 'title': f'Engineering note {i:05d}',
             'description': f'A practical note about {tag}.', 'tag': tag} for i in ids]


class BackgroundLoad:
    def __init__(self, clients, tag, offset):
        self.clients, self.tag, self.offset = clients, tag, offset
        self.stop = threading.Event()
        self.records = []
        self.threads = []
        self.started = None
        self.finished = None

    def worker(self, client):
        while not self.stop.is_set() and time.monotonic() - self.started < 45:
            start = time.monotonic()
            record = {'client': client, 'start_seconds': start - self.started}
            try:
                value = read_json(f'{ORIGIN}/articles?tag={self.tag}&offset={self.offset}')
                if value['articlesCount'] != 25000 or len(value['articles']) != 20:
                    raise AssertionError('Invalid background response')
                record.update(status='ok', backend=value['backend'])
            except Exception as error:
                record.update(status='failed', error=str(error))
                self.stop.set()
            record['end_seconds'] = time.monotonic() - self.started
            self.records.append(record)

    def start(self):
        self.started = time.monotonic()
        for client in range(self.clients):
            thread = threading.Thread(target=self.worker, args=(client,), daemon=True)
            self.threads.append(thread)
            thread.start()
        deadline = time.monotonic() + 10
        while len({r['client'] for r in self.records if r['status'] == 'ok'}) < self.clients:
            if self.stop.is_set() or time.monotonic() > deadline:
                raise RuntimeError('Background clients failed to become ready')
            time.sleep(0.01)

    def close(self):
        self.stop.set()
        for thread in self.threads:
            thread.join(timeout=12)
        self.finished = time.monotonic()
        if any(thread.is_alive() for thread in self.threads):
            raise RuntimeError('Background client failed to stop')

    def summary(self, browser_start=None, browser_end=None):
        successful = [r for r in self.records if r['status'] == 'ok']
        elapsed = self.finished - self.started
        overlap = [] if browser_start is None else [r for r in successful
                   if r['end_seconds'] >= browser_start and r['start_seconds'] <= browser_end]
        return {'clients': self.clients, 'duration_seconds': elapsed,
                'successful_requests': len(successful), 'failed_requests': len(self.records) - len(successful),
                'throughput_per_second': len(successful) / elapsed,
                'requests_overlapping_browser_trial': len(overlap),
                'query_cpu_seconds': sum(r['backend']['query_thread_cpu_seconds'] for r in successful)}


def measure(browser, base, trial, output):
    context = browser.new_context(viewport={'width': 1365, 'height': 900}, service_workers='block')
    try:
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('requestfailed', lambda request: errors.append(f'{request.url}: {request.failure}'))
        page.on('response', lambda response: errors.append(f'HTTP {response.status}: {response.url}') if response.status >= 400 else None)
        cdp = context.new_cdp_session(page)
        profile = PROFILES[trial['profile']]
        cdp.send('Network.enable')
        cdp.send('Network.emulateNetworkConditions', {
            'offline': False, 'latency': profile['latency_ms'],
            'downloadThroughput': profile['mbps'] * 1e6 / 8,
            'uploadThroughput': profile['mbps'] * 1e6 / 8})
        cdp.send('Emulation.setCPUThrottlingRate', {'rate': profile['cpu_rate']})
        before = read_json(base + '/api/telemetry')
        response = page.goto(f"{base}/feed/{trial['strategy']}?tag={trial['tag']}&offset={trial['offset']}&query_mode={trial.get('query_mode', 'scan')}", wait_until='load')
        if response.status != 200:
            raise AssertionError(f'Navigation HTTP {response.status}')
        page.wait_for_selector('main[data-ready="true"]')
        after = read_json(base + '/api/telemetry')
        observed = page.locator('article').evaluate_all("""nodes => nodes.map(n => ({
          slug: n.dataset.slug, title: n.querySelector('h2').textContent,
          description: n.querySelector('[data-description]').textContent,
          tag: n.querySelector('[data-tag]').textContent
        }))""")
        if observed != expected_articles(trial['tag'], trial['offset']):
            raise AssertionError('Article content, order, or pagination mismatch')
        if page.locator('#article-count').inner_text() != '25000':
            raise AssertionError('Article total mismatch')
        backend = json.loads(page.locator('main').get_attribute('data-backend'))
        metrics = page.evaluate("""() => {
          const nav = performance.getEntriesByType('navigation')[0];
          const ready = performance.getEntriesByName('feed-interactive')[0];
          return { feed_interactive_ms: ready?.startTime ?? null,
            ttfb_ms: nav.responseStart,
            transfer_bytes: nav.transferSize + performance.getEntriesByType('resource').reduce((s, r) => s + r.transferSize, 0) };
        }""")
        if metrics['feed_interactive_ms'] is None:
            raise AssertionError('Readiness marker missing')
        if before['pid'] != after['pid']:
            raise AssertionError('Next server restarted during measurement')
        metrics['next_process_cpu_seconds'] = sum(after['cpu'][k] - before['cpu'][k] for k in ['user', 'system']) / 1e6
        metrics['next_process_cpu_window_seconds'] = after['uptime'] - before['uptime']
        button = page.locator('article button').first
        button.click()
        page.wait_for_function("document.querySelector('#saved-count').textContent === '1'")
        if button.get_attribute('aria-pressed') != 'true':
            raise AssertionError('Save state mismatch')
        button.click()
        page.wait_for_function("document.querySelector('#saved-count').textContent === '0'")
        if errors:
            raise AssertionError(str(errors))
        if trial.get('index') == 0:
            page.screenshot(path=str(output / 'pilot-check.png'))
        return {**trial, 'status': 'ok', 'correctness': True, 'backend': backend, 'metrics': metrics,
                'dom_sha256': hashlib.sha256(json.dumps(observed, sort_keys=True).encode()).hexdigest()}
    finally:
        context.close()


def summarize(rows, output):
    lines = ['# Article contention pilot', '', 'Three temporal blocks on one machine; descriptive only.', '',
             '| Profile | Background clients | Strategy | Passed | Median ready ms | Median origin queue ms | Median query CPU ms |',
             '|---|---|---|---|---|---|---|']
    for profile in PROFILES:
        for clients in [0, 2]:
            for strategy in ['csr', 'ssr']:
                group = [r for r in rows if (r['profile'], r['clients'], r['strategy']) == (profile, clients, strategy)]
                good = [r for r in group if r['status'] == 'ok']
                med = lambda fn: f'{statistics.median(fn(r) for r in good):.2f}' if good else '—'
                lines.append(f"| {profile} | {clients} | {strategy} | {len(good)}/{len(group)} | {med(lambda r: r['metrics']['feed_interactive_ms'])} | {med(lambda r: r['backend']['queue_ms'])} | {med(lambda r: r['backend']['query_thread_cpu_seconds'] * 1000)} |")
    lines += ['', '## Block-paired differences', '', 'SSR minus CSR readiness (negative favors SSR):', '',
              '| Profile | Background clients | Block 0 ms | Block 1 ms | Block 2 ms |', '|---|---|---|---|---|']
    for profile in PROFILES:
        for clients in [0, 2]:
            diffs = []
            for block in range(3):
                group = {r['strategy']: r for r in rows if r['profile'] == profile and r['clients'] == clients and r['block'] == block and r['status'] == 'ok'}
                diffs.append(f"{group['ssr']['metrics']['feed_interactive_ms'] - group['csr']['metrics']['feed_interactive_ms']:.2f}" if len(group) == 2 else '—')
            lines.append(f"| {profile} | {clients} | {' | '.join(diffs)} |")
    lines += ['', 'Input topic/pagination changes across blocks. These are not independent machine/session replicates.',
              'Concurrent origin requests create actual SQLite CPU work and queueing. The single connection and scan query are explicit implementation choices.',
              'Any rank reversal is exploratory; no learned-policy advantage or production generalization is established.']
    (output / 'summary.md').write_text('\n'.join(lines) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:3103')
    parser.add_argument('--output-dir')
    args = parser.parse_args()
    if urlparse(args.base_url).hostname not in {'localhost', '127.0.0.1'}:
        parser.error('Only local benchmark servers are supported')
    output = Path(args.output_dir or run_directory('contention-pilot'))
    output.mkdir(parents=True, exist_ok=False)
    paths = [p for p in (ROOT / 'apps/benchmark').rglob('*') if p.is_file() and '.next' not in p.parts]
    paths += [ROOT / p for p in ['experiments/contention_backend.py', 'experiments/contention_suite.py',
              'experiments/browser_pilot.py', 'src/env/provenance.py', 'tests/test_contention_backend.py',
              'docs/research/CONTENTION_PILOT_PROTOCOL.md', 'package.json', 'package-lock.json',
              'requirements-research.lock.txt', '.nvmrc']]
    for path in paths:
        dest = output / 'source' / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    trials = []
    rng = random.Random(20260921)
    for block in range(3):
        conditions = [{'block': block, 'tag': 'accessibility' if block == 1 else 'rendering', 'offset': block * 20,
                       'profile': profile, 'clients': clients, 'strategy': strategy}
                      for profile in PROFILES for clients in [0, 2] for strategy in ['csr', 'ssr']]
        rng.shuffle(conditions)
        trials.extend(conditions)
    rows = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=True)
        try:
            health = read_json(ORIGIN + '/health')
            if health['rows'] != 50000 or health['imposed_delay_ms'] != 0:
                raise ValueError('Origin configuration differs from protocol')
            smoke = []
            for tag in ['rendering', 'accessibility']:
                for offset in [0, 20]:
                    for strategy in ['csr', 'ssr']:
                        result = measure(browser, args.base_url, {'tag': tag, 'offset': offset,
                                         'strategy': strategy, 'profile': 'local-desktop'}, output)
                        smoke.append({'tag': tag, 'offset': offset, 'strategy': strategy, 'status': result['status']})
            manifest = {'purpose': 'article_contention_engineering_pilot', 'schema_version': 1,
                        'source': source_metadata(), 'browser_version': browser.version, 'origin': health,
                        'build_id': (ROOT / 'apps/benchmark/.next/BUILD_ID').read_text().strip(),
                        'source_sha256': {str(p.relative_to(ROOT)): file_hash(p) for p in paths},
                        'trials': trials, 'profiles': PROFILES, 'order_seed': 20260921, 'semantic_checks': smoke}
            (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
            with (output / 'measurements.jsonl').open('x') as stream, (output / 'background.jsonl').open('x') as background:
                for index, trial in enumerate(trials):
                    trial = {**trial, 'index': index}
                    load = BackgroundLoad(trial['clients'], trial['tag'], trial['offset'])
                    nav_start = nav_end = None
                    try:
                        load.start()
                        nav_start = time.monotonic() - load.started
                        row = measure(browser, args.base_url, trial, output)
                        nav_end = time.monotonic() - load.started
                    except Exception as error:
                        row = {**trial, 'status': 'failed', 'error': str(error)}
                    finally:
                        load.close()
                    row['load'] = load.summary(nav_start, nav_end or (load.finished - load.started))
                    if row['load']['failed_requests'] or (trial['clients'] and not row['load']['requests_overlapping_browser_trial']):
                        row.update(status='failed', error='Background load failed or did not overlap the measurement')
                    for record in load.records:
                        background.write(json.dumps({'trial_index': index, **record}) + '\n')
                    background.flush()
                    rows.append(row)
                    stream.write(json.dumps(row) + '\n'); stream.flush()
                    print(f"{index + 1}/24 {trial['strategy']} clients={trial['clients']}: {row['status']}", flush=True)
            summarize(rows, output)
            print(f'Results: {output}')
            if any(r['status'] != 'ok' for r in rows):
                raise SystemExit('Failed trials retained; inspect before interpreting results')
        finally:
            browser.close()


if __name__ == '__main__':
    main()
