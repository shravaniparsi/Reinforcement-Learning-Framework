"""Fresh GitHub Linux builds and engineering checks. No study collection or fitting."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
EXTERNAL = ROOT / 'experiments/vendor/svelte-realworld'
UPSTREAM = 'df796708040f5200ec572b28ab7f88ecee5794dd'
CHROME = '154.0.8037.57'
ADAPTER = ROOT / 'experiments/recovery_v5/buffered-data.js'
PATCH = ROOT / 'experiments/external/svelte-realworld/production-variants.patch'
sys.path.insert(0, str(ROOT / 'experiments'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def fresh_runner_only():
    if os.environ.get('GITHUB_ACTIONS') != 'true' or platform.system() != 'Linux':
        raise RuntimeError('This entry point requires a fresh GitHub-hosted Linux job')
    if os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted':
        raise RuntimeError('Self-hosted runners are not authorized for this build')
    if os.environ.get('GITHUB_WORKSPACE') != str(ROOT):
        raise RuntimeError('Run from the checked-out GitHub workspace')


def command(args, output, name, cwd=ROOT, overrides=None):
    with (output / (name + '.log')).open('x') as log:
        subprocess.run(args, cwd=cwd, env={**os.environ, **(overrides or {})},
                       stdout=log, stderr=subprocess.STDOUT, check=True)


def fingerprint(directory):
    return {str(p.relative_to(directory)): sha(p) for p in sorted(directory.rglob('*'))
            if p.is_file() and 'cache' not in p.relative_to(directory).parts and p.name != 'trace'}


def builds():
    locations = {'next': ROOT / 'apps/benchmark/.next',
                 'ssr': EXTERNAL / 'build-ssr', 'csr': EXTERNAL / 'build-csr'}
    if not (locations['next'] / 'BUILD_ID').is_file():
        raise ValueError('Missing Next production build')
    if any(not (locations[m] / 'index.js').is_file() for m in ('ssr', 'csr')):
        raise ValueError('Missing external production builds')
    return {key: fingerprint(path) for key, path in locations.items()}


def checksums(output):
    files = sorted(p for p in output.rglob('*') if p.is_file() and p.name != 'checksums.sha256')
    (output / 'checksums.sha256').write_text(''.join(f'{sha(p)}  {p.relative_to(output)}\n' for p in files))


def prepare(output):
    fresh_runner_only()
    if EXTERNAL.exists() or (ROOT / 'apps/benchmark/.next').exists():
        raise ValueError('Refusing to reuse or overwrite an existing application build')
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'build-manifest.json').exists():
        raise ValueError('Build attempt already recorded; use a new job')
    manifest = {'purpose': 'github_linux_engineering_only', 'eligible_for_main_study': False,
                'validation': 'running', 'started_utc': datetime.now(timezone.utc).isoformat(),
                'git_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'platform': platform.platform(), 'python': sys.version,
                'runner': {k: os.environ.get(k) for k in ['GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT',
                    'GITHUB_REF','RUNNER_ARCH','RUNNER_OS','RUNNER_ENVIRONMENT','ImageOS','ImageVersion']}}
    try:
        for name, args in [('cpu', ['lscpu']), ('memory', ['free', '-b']),
                           ('node', ['node', '--version']), ('python-packages', [sys.executable, '-m', 'pip', 'freeze'])]:
            command(args, output, name)
        EXTERNAL.parent.mkdir(parents=True, exist_ok=True)
        command(['git', 'init', str(EXTERNAL)], output, 'external-init')
        command(['git', 'remote', 'add', 'origin', 'https://github.com/sveltejs/realworld.git'], output, 'external-remote', EXTERNAL)
        command(['git', 'fetch', '--depth=1', 'origin', UPSTREAM], output, 'external-fetch', EXTERNAL)
        command(['git', 'checkout', '--detach', UPSTREAM], output, 'external-checkout', EXTERNAL)
        command(['git', 'apply', str(PATCH)], output, 'external-patch', EXTERNAL)
        shutil.copy2(ADAPTER, EXTERNAL / 'static/buffered-data.v1.js')
        html = EXTERNAL / 'src/app.html'
        text = html.read_text(); needle = '\t\t%sveltekit.head%'
        if text.count(needle) != 1:
            raise ValueError('Unexpected upstream template; do not guess integration')
        html.write_text(text.replace(needle, '\t\t<script src="/buffered-data.v1.js"></script>\n' + needle))
        command(['corepack', 'pnpm', 'install', '--frozen-lockfile'], output, 'external-install', EXTERNAL)
        for mode in ('ssr', 'csr'):
            command(['corepack', 'pnpm', 'run', 'build'], output, 'build-' + mode, EXTERNAL,
                    {'PUBLIC_PILOT_SSR': 'true' if mode == 'ssr' else 'false', 'PILOT_BUILD_OUT': 'build-' + mode})
        command(['node', str(ROOT / 'node_modules/next/dist/bin/next'), 'build', 'apps/benchmark', '--webpack'], output, 'build-next')
        manifest.update(upstream_commit=UPSTREAM, patch_sha256=sha(PATCH), adapter_sha256=sha(ADAPTER),
                        root_lock_sha256=sha(ROOT / 'package-lock.json'),
                        external_lock_sha256=sha(EXTERNAL / 'pnpm-lock.yaml'), builds=builds(), validation='passed')
        tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
        manifest['source_sha256'] = {p: sha(ROOT / p) for p in tracked if p and (ROOT / p).is_file()}
        command(['git', 'diff', '--', '.', ':!pnpm-lock.yaml'], output, 'external-adaptation', EXTERNAL)
    except Exception as error:
        manifest.update(validation='failed', failure=str(error))
        raise
    finally:
        write(output / 'build-manifest.json', manifest)
        checksums(output)


class CheckedContext:
    def __init__(self, inner, checks):
        self.inner, self.checks = inner, checks

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def close(self):
        try:
            for page in self.inner.pages:
                installed = page.evaluate("globalThis[Symbol.for('rl-rendering.buffered-data.v1')] === true")
                self.checks.append(installed)
                if not installed:
                    raise ValueError('Buffered adapter was not installed by the application')
        finally:
            self.inner.close()


class CheckedBrowser:
    def __init__(self, inner, checks):
        self.inner, self.checks = inner, checks

    def new_context(self, **kwargs):
        return CheckedContext(self.inner.new_context(**kwargs), self.checks)


def validate(rows, schedule, adapter_checks):
    from main_study_design import validate_session
    validate_session(rows, schedule)
    if any(row.get('errors') or row.get('external_requests') for row in rows):
        raise ValueError('Browser errors or nonlocal requests retained; check failed')
    if not adapter_checks or not all(adapter_checks):
        raise ValueError('Missing or failed integrated adapter checks')


def check(output, chrome):
    fresh_runner_only()
    from main_study_runner import measure, delivery, servers
    from main_study_design import session_schedule
    from playwright.sync_api import sync_playwright
    receipt = json.loads((output / 'build-manifest.json').read_text())
    if receipt['validation'] != 'passed' or receipt['builds'] != builds():
        raise ValueError('Build receipt failed or production bytes changed')
    if (output / 'engineering-manifest.json').exists():
        raise ValueError('Engineering attempt already recorded; use a new job')
    schedule = session_schedule('engineering', 0)
    manifest = {'purpose': 'github_linux_engineering_only', 'eligible_for_main_study': False,
                'collection_enabled': ['engineering'], 'validation': 'running', 'schedule': schedule,
                'browser_executable_sha256': sha(chrome), 'adapter_injected_by_collector': False,
                'adapter_install_checks': [], 'preflight': [], 'network': 'unthrottled-loopback'}
    rows = []
    write(output / 'engineering-manifest.json', manifest)
    try:
        with servers(shutil.which('node'), output) as processes, sync_playwright() as pw:
            manifest['processes'] = processes
            for port in (3106, 3107):
                with urlopen(f'http://127.0.0.1:{port}/') as response:
                    if response.read().decode().count('<script src="/buffered-data.v1.js"></script>') != 1:
                        raise ValueError('Missing or duplicated adapter startup script')
                with urlopen(f'http://127.0.0.1:{port}/buffered-data.v1.js') as response:
                    if response.read() != ADAPTER.read_bytes():
                        raise ValueError('Served adapter bytes differ')
            browser = pw.chromium.launch(executable_path=str(chrome), headless=True)
            manifest['browser_version'] = browser.version
            try:
                if browser.version != CHROME:
                    raise ValueError('Browser version differs from the CI pin')
                seen, warmed = set(), set()
                def measured(trial, capture=False):
                    wrapped = CheckedBrowser(browser, manifest['adapter_install_checks']) if trial['application'] == 'external' else browser
                    return measure(wrapped, trial, output, capture=capture)
                for trial in schedule['trials']:
                    key = (trial['application'], trial['action'], trial['case_id'])
                    if key not in seen:
                        manifest['preflight'].append(delivery(trial)); seen.add(key)
                    if key[:2] not in warmed:
                        row = measured({**trial, 'cpu_rate': 1, 'cache': 'cold'}, capture=True)
                        manifest['preflight'].append({'warmup': key[:2], 'record': row})
                        if row['status'] != 'ok' or not row['correctness'] or row['errors'] or row['external_requests']:
                            raise ValueError('Warmup failed; evidence retained')
                        warmed.add(key[:2])
                with (output / 'engineering.jsonl').open('x') as stream:
                    for trial in schedule['trials']:
                        row = measured(trial); rows.append(row)
                        stream.write(json.dumps(row) + '\n'); stream.flush()
                        print(f'{len(rows)}/72 {trial["application"]} {trial["action"]}: {row["status"]}', flush=True)
            finally:
                browser.close()
        validate(rows, schedule, manifest['adapter_install_checks'])
        if builds() != receipt['builds']:
            raise ValueError('Production build changed during engineering check')
        manifest['validation'] = 'passed'
    except Exception as error:
        manifest.update(validation='failed', failure=str(error))
        raise
    finally:
        manifest['observations'] = len(rows)
        write(output / 'engineering-manifest.json', manifest)
        checksums(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['prepare', 'check'])
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--chrome', type=Path)
    args = parser.parse_args()
    if args.operation == 'prepare':
        prepare(args.output.resolve())
    else:
        if not args.chrome:
            parser.error('check requires --chrome')
        check(args.output.resolve(), args.chrome.resolve())


if __name__ == '__main__':
    main()
