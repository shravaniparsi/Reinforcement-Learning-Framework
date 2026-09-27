"""Common engineering collection for three workflows. Confirmatory stages fail closed.

Uses existing mount/hydration marks, NOT the proposed interaction-ready endpoint.
Every run starts/stops its own five local servers and a new browser.
"""
import argparse
import fcntl
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen
from playwright.sync_api import sync_playwright
from main_study_design import ROOT, authorize_collection, session_schedule, validate_session, digest
from network_quiet import NetworkQuiet
from browser_pilot import read_json
from contention_suite import expected_articles
from external_realworld_smoke import expected as external_expected, verify as external_verify

EXTERNAL = ROOT / 'experiments/vendor/svelte-realworld'
BASES = {'catalog': 'http://127.0.0.1:3104', 'articles': 'http://127.0.0.1:3104',
         'ssr': 'http://127.0.0.1:3106', 'csr': 'http://127.0.0.1:3107'}
MARKS = {'catalog': 'catalog-interactive', 'articles': 'feed-interactive', 'external': 'external-feed-interactive'}
OBSERVE = """(() => {
 window.__studyLcp = [];
 new PerformanceObserver(list => { for (const e of list.getEntries()) window.__studyLcp.push({
   startTime:e.startTime, size:e.size, element:e.element?.tagName ?? null,
   text:e.element?.textContent?.slice(0,100) ?? null});
 }).observe({type:'largest-contentful-paint', buffered:true});
})();"""

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_files():
    paths = list((ROOT / 'experiments').glob('*.py'))
    paths += [p for p in (ROOT / 'apps/benchmark').rglob('*') if p.is_file() and '.next' not in p.parts and 'node_modules' not in p.parts]
    paths += [ROOT / p for p in ['src/env/provenance.py', 'package.json', 'package-lock.json',
              'requirements-research.lock.txt', 'docs/research/MAIN_STUDY_PROTOCOL_v1.md',
              'docs/research/MAIN_STUDY_RUNNER.md', 'docs/research/MAIN_STUDY_CAMPAIGN.md', 'experiments/main-study-schedule-v1.json']]
    paths += list((ROOT / 'experiments/external/svelte-realworld').glob('*'))
    return sorted(set(p for p in paths if p.is_file()))

def build_fingerprint():
    meta = json.loads((ROOT / 'experiments/external/svelte-realworld/production-builds.json').read_text())
    for mode, build in meta['builds'].items():
        for name, expected_sha in build['sha256'].items():
            if sha(EXTERNAL / build['output'] / name) != expected_sha:
                raise ValueError(f'External build changed: {mode}/{name}')
    next_dir = ROOT / 'apps/benchmark/.next'
    if not (next_dir / 'BUILD_ID').is_file():
        raise ValueError('Build the Next benchmark before collection')
    files = {str(p.relative_to(next_dir)): sha(p) for p in sorted(next_dir.rglob('*'))
             if p.is_file() and 'cache' not in p.relative_to(next_dir).parts and p.name != 'trace'}
    return {'external': meta, 'next_files_sha256': files,
            'next_build_id': (next_dir / 'BUILD_ID').read_text().strip()}

def assert_ports_available(ports):
    # A closed listener can leave TIME_WAIT connections. Reuse ignores that state,
    # but binding still rejects an actual listener on the same address/port.
    for port in ports:
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(('127.0.0.1', port))
            except OSError as error:
                raise OSError(f'Benchmark port {port} unavailable: {error}') from error

@contextmanager
def servers(node, output):
    specs = [
        ('article-api', 3203, [sys.executable, str(ROOT/'experiments/contention_backend.py')], ROOT, {}, '/health'),
        ('external-api', 3205, [sys.executable, str(ROOT/'experiments/external_realworld_backend.py')], ROOT, {}, '/api/tags'),
        ('next', 3104, [node, str(ROOT/'node_modules/next/dist/bin/next'), 'start', str(ROOT/'apps/benchmark'), '-p', '3104', '-H', '127.0.0.1'], ROOT, {}, '/api/telemetry'),
        ('external-ssr', 3106, [node, 'build-ssr/index.js'], EXTERNAL, {'HOST':'127.0.0.1','PORT':'3106','ORIGIN':BASES['ssr']}, '/pilot-telemetry'),
        ('external-csr', 3107, [node, 'build-csr/index.js'], EXTERNAL, {'HOST':'127.0.0.1','PORT':'3107','ORIGIN':BASES['csr']}, '/pilot-telemetry'),
    ]
    # Refuse to attach to an existing service: each engineering session owns its processes.
    assert_ports_available([port for _, port, *_ in specs])
    processes, logs, records = [], [], []
    try:
        for name, port, command, cwd, overrides, health in specs:
            log = (output / f'{name}.log').open('x'); logs.append(log)
            proc = subprocess.Popen(command, cwd=cwd, env={**os.environ, **overrides}, stdout=log, stderr=subprocess.STDOUT)
            processes.append(proc)
            records.append({'name':name, 'pid':proc.pid, 'command':command, 'port':port})
            deadline = time.monotonic() + 30
            while True:
                if proc.poll() is not None:
                    raise RuntimeError(f'{name} exited during startup; see retained log')
                try:
                    with urlopen(f'http://127.0.0.1:{port}{health}', timeout=1) as response:
                        if response.status == 200: break
                except OSError:
                    if time.monotonic() > deadline: raise TimeoutError(f'{name} startup timed out')
                    time.sleep(.1)
        yield records
    finally:
        for proc in reversed(processes):
            if proc.poll() is None: proc.terminate()
        for proc in reversed(processes):
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill(); proc.wait()
        for log in logs: log.close()

def route(trial):
    app, action = trial['application'], trial['action']
    if app == 'external':
        base = BASES[action]
        path = '/?page=1' + (f"&tag={trial['tag']}" if trial['tag'] else '')
    else:
        base = BASES[app]
        path = f'/{action}' if app == 'catalog' else f"/feed/{action}?tag={trial['tag']}&offset={trial['offset']}&query_mode=indexed"
    return base, base + path

def content(page, trial):
    app = trial['application']
    if app == 'catalog':
        expected = [{'id':f'product-{i+1}', 'name':f'Desk accessory {i+1:02d}', 'price':f'{(1200+i*175)/100:.2f}'} for i in range(24)]
        observed = page.locator('article[data-product-id]').evaluate_all("nodes => nodes.map(n => ({id:n.dataset.productId,name:n.querySelector('h2').textContent,price:n.querySelector('[data-price]').textContent}))")
        assert page.locator('main').get_attribute('data-version') == 'catalog-v1'
    elif app == 'articles':
        expected = expected_articles(trial['tag'], trial['offset'])
        observed = page.locator('article[data-slug]').evaluate_all("nodes => nodes.map(n => ({slug:n.dataset.slug,title:n.querySelector('h2').textContent,description:n.querySelector('[data-description]').textContent,tag:n.querySelector('[data-tag]').textContent}))")
        assert page.locator('#article-count').inner_text() == '25000'
    else:
        external_verify(page, trial['tag'], 1)
        observed = expected = external_expected(trial['tag'], 1)
    if observed != expected: raise ValueError('Content/order mismatch')
    return digest(observed)

def interaction(page, trial):
    network = NetworkQuiet(page)
    app = trial['application']
    if app == 'catalog':
        page.locator('article button').first.click()
        page.wait_for_function("document.querySelector('#cart-count').textContent === '1'")
        assert page.locator('#cart-total').inner_text() == '12.00'
        return 'add-to-cart'
    if app == 'articles':
        button = page.locator('article button').first
        button.click()
        page.wait_for_function("document.querySelector('#saved-count').textContent === '1'")
        assert button.get_attribute('aria-pressed') == 'true'
        button.click()
        page.wait_for_function("document.querySelector('#saved-count').textContent === '0'")
        assert button.get_attribute('aria-pressed') == 'false'
        return 'save-and-remove'
    base, _ = route(trial)
    page.locator('.sidebar .tag-list a', has_text='rendering').click()
    page.wait_for_url(lambda url: url.startswith(base) and 'tag=rendering' in url)
    external_verify(page, 'rendering', 1)
    network.wait()
    page.locator('.pagination a', has_text='2').click()
    page.wait_for_url(lambda url: url.startswith(base) and 'tag=rendering' in url and 'page=2' in url)
    external_verify(page, 'rendering', 2)
    network.wait()
    return 'tag-and-pagination'

def measure(browser, trial, output, capture=False):
    base, url = route(trial)
    app = trial['application']
    context = browser.new_context(viewport={'width':1365,'height':900}, service_workers='block')
    errors, external = [], []
    row = {**trial, 'status':'failed', 'correctness':False, 'metrics':None, 'errors':errors, 'external_requests':external}
    if capture: context.tracing.start(screenshots=True, snapshots=True)
    try:
        context.add_init_script(OBSERVE)
        page = context.new_page(); page.set_default_timeout(30000)
        network = NetworkQuiet(page)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('requestfailed', lambda r: errors.append(f'{r.url}: {r.failure}'))
        page.on('response', lambda r: errors.append(f'HTTP {r.status}: {r.url}') if r.status >= 400 else None)
        page.on('request', lambda r: external.append(r.url) if urlparse(r.url).hostname not in {'localhost','127.0.0.1',None} else None)
        cdp = context.new_cdp_session(page)
        cdp.send('Network.enable')
        cdp.send('Emulation.setCPUThrottlingRate', {'rate':trial['cpu_rate']})
        ready = "document.documentElement.dataset.feedReady === 'true'" if app == 'external' else "document.querySelector('main')?.dataset.ready === 'true'"
        if trial['cache'] == 'warm':
            page.goto(url, wait_until='load', timeout=30000)
            page.wait_for_function(ready)
            content(page, trial)
            network.wait()
        telemetry = base + ('/pilot-telemetry' if app == 'external' else '/api/telemetry')
        before = read_json(telemetry)
        response = page.goto(url, wait_until='load', timeout=30000)
        if response.status != 200: raise ValueError('Navigation failed')
        page.wait_for_function(ready)
        after = read_json(telemetry)
        row['content_sha256'] = content(page, trial)
        # Fixed paint observation: at least one second after the application marker, before scripted interaction.
        page.wait_for_function('(mark) => performance.now() >= performance.getEntriesByName(mark)[0].startTime + 1000', arg=MARKS[app])
        row['metrics'] = page.evaluate("""mark => {
          const nav=performance.getEntriesByType('navigation')[0];
          const lcp=window.__studyLcp.at(-1) ?? null;
          return {mount_hydration_ms:performance.getEntriesByName(mark)[0]?.startTime ?? null,
            paint_observation_end_ms:performance.now(), fcp_ms:performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? null,
            lcp_ms:lcp?.startTime ?? null, lcp_candidate:lcp, ttfb_ms:nav.responseStart};
        }""", MARKS[app])
        if row['metrics']['mount_hydration_ms'] is None or before['pid'] != after['pid']:
            raise ValueError('Missing marker or server restart')
        row['metrics']['server_cpu_seconds'] = sum(after['cpu'][k]-before['cpu'][k] for k in ['user','system'])/1e6
        row['metrics']['server_cpu_window_seconds'] = after['uptime']-before['uptime']
        network.wait()
        row['metrics']['transfer_bytes'] = page.evaluate("() => performance.getEntriesByType('navigation')[0].transferSize + performance.getEntriesByType('resource').reduce((s,r)=>s+r.transferSize,0)")
        if app == 'articles':
            row['backend'] = json.loads(page.locator('main').get_attribute('data-backend'))
            if row['backend']['query_mode'] != 'indexed': raise ValueError('Wrong backend mode')
        if capture: page.screenshot(path=str(output / f'{app}-{trial["action"]}.png'))
        row['interaction'] = interaction(page, trial)
        network.wait()
        if errors or external: raise ValueError('Browser/request/external-origin checks failed')
        row.update(status='ok', correctness=True)
    except Exception as error:
        row['error'] = str(error)
    finally:
        if capture:
            context.tracing.stop(path=str(output / f'{app}-{trial["action"]}-trace.zip'))
        context.close()
    return row

def delivery(trial):
    _, url = route(trial)
    with urlopen(url, timeout=10) as response: html = response.read().decode()
    app = trial['application']
    if app == 'catalog': marker = '<article data-product-id="product-1"'
    elif app == 'articles': marker = f'<article data-slug="{expected_articles(trial["tag"],trial["offset"])[0]["slug"]}"'
    else: marker = f'<h1>{external_expected(trial["tag"],1)[0]["title"]}</h1>'
    actual = marker in html
    if actual != (trial['action'] == 'ssr'): raise ValueError('Initial HTML treatment mismatch')
    return {'application':app, 'action':trial['action'], 'case_id':trial['case_id'], 'content_in_initial_html':actual}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    parser.add_argument('--node', required=True)
    parser.add_argument('--stage', default='engineering')
    parser.add_argument('--campaign', type=Path)
    parser.add_argument('--session-index', type=int, default=0)
    args = parser.parse_args()
    launch_sha, lock, artifacts = None, None, {}
    if args.stage == 'engineering':
        authorize_collection(args.stage)
        if args.output is None or args.campaign is not None:
            parser.error('Engineering requires --output and no --campaign')
        schedule = session_schedule('engineering', 0)
    else:
        if args.campaign is None or args.output is not None:
            parser.error('Main stages require --campaign and no --output')
        from main_study_campaign import verify_lock, collection_gate
        # Advisory OS lock prevents two collectors claiming the same campaign slot.
        campaign_guard = (args.campaign/'collector.lock').open('a')
        fcntl.flock(campaign_guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock, launch_sha = verify_lock(args.campaign,args.node)
        args.output, schedule, artifacts = collection_gate(args.campaign,args.stage,args.session_index,launch_sha)
    builds = build_fingerprint()
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {'schema_version':1, 'purpose':'engineering_validation_only', 'eligible_for_main_study':False,
                'endpoint':'mount/hydration; interactions are separate correctness checks',
                'started_utc':datetime.now(timezone.utc).isoformat(), 'host':platform.platform(),
                'host_load_average':os.getloadavg(), 'python':sys.version, 'builds':builds, 'schedule':schedule,
                'node_version':subprocess.check_output([args.node,'--version'],text=True).strip(),
                'network':'unthrottled-loopback', 'source_sha256':{}}
    if lock:
        manifest.update(purpose='main_study',eligible_for_main_study=True,endpoint='mount_hydration_ms',
                        launch_lock_sha256=launch_sha,policy_artifacts=artifacts)
    for path in source_files():
        relative = path.relative_to(ROOT)
        dest = args.output/'source'/relative; dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,dest); manifest['source_sha256'][str(relative)] = sha(path)
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    rows = []
    try:
        with servers(args.node,args.output) as processes, sync_playwright() as pw:
            browser = pw.chromium.launch(channel='chrome',headless=True)
            try:
                manifest.update(processes=processes,browser_version=browser.version)
                (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
                if lock and browser.version != lock['browser_version']:
                    raise ValueError('Browser changed since launch lock')
                # All 18 action/content variants checked; independent fresh contexts warm each server action once.
                seen, warmed, checks = set(), set(), []
                for trial in schedule['trials']:
                    key = (trial['application'],trial['action'],trial['case_id'])
                    if key not in seen: checks.append(delivery(trial)); seen.add(key)
                    action = key[:2]
                    if action not in warmed:
                        warm = measure(browser,{**trial,'cpu_rate':1,'cache':'cold'},args.output,capture=True)
                        checks.append({'server_warmup':action,'record':warm})
                        if warm['status'] != 'ok': raise ValueError(f'Preflight failed: {warm}')
                        warmed.add(action)
                manifest['preflight'] = checks
                (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
                with (args.output/'measurements.jsonl').open('x') as stream:
                    for trial in schedule['trials']:
                        row = measure(browser,trial,args.output)
                        rows.append(row); stream.write(json.dumps(row)+'\n'); stream.flush()
                        print(f"{len(rows)}/72 {trial['application']} {trial['action']} {trial['cache']}: {row['status']}",flush=True)
                validate_session(rows,schedule)
                if lock:
                    verify_lock(args.campaign,args.node)
                    # Input artifact files are checked directly; the current session is not yet complete.
                    from main_study_policies import read_artifact
                    for field,name,kind in [('training_fit_sha256','training-fit.json','training_fit'),
                                            ('frozen_policy_sha256','policies.json','frozen_policies')]:
                        if field in artifacts and digest(read_artifact(args.campaign/'artifacts'/name,kind)) != artifacts[field]:
                            raise ValueError('Policy artifact changed during collection')
                (args.output/'validation.json').write_text(json.dumps({'status':'passed','observations':72,
                    'main_study_eligible':bool(lock),'note':'Complete session; main eligibility requires its verified campaign lock' if lock else 'Engineering only'},indent=2)+'\n')
            finally: browser.close()
    except Exception as error:
        (args.output/'failure.json').write_text(json.dumps({'error':str(error),'records_retained':len(rows)},indent=2)+'\n')
        raise
    finally:
        files = sorted(p for p in args.output.rglob('*') if p.is_file() and p.name != 'checksums.sha256')
        (args.output/'checksums.sha256').write_text(''.join(f'{sha(p)}  {p.relative_to(args.output)}\n' for p in files))
    print(f'{args.stage} archive: {args.output}')

if __name__ == '__main__': main()
