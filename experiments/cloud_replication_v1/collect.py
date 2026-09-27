"""Separate cloud cohort. Reuses measurement/build code without changing the Mac study."""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import urlopen
from design import ROOT, PURPOSE, schedule, verify_lock
sys.path.insert(0, str(ROOT / 'experiments'))
from ci_engineering.run import (fresh_runner_only, builds, sha, write, checksums,
                               CheckedBrowser, validate, ADAPTER, CHROME)

def collect(output, chrome, index):
    fresh_runner_only()
    lock_sha = verify_lock()
    if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise ValueError("Reruns are ineligible; preserve and investigate the original attempt")
    if receipt_sha := os.environ.get("GITHUB_SHA"):
        if len(receipt_sha) != 40:
            raise ValueError("Invalid workflow commit")
    else:
        raise ValueError("Missing workflow commit")
    from main_study_runner import measure, delivery, servers
    from playwright.sync_api import sync_playwright
    receipt = json.loads((output / 'build-manifest.json').read_text())
    if receipt['git_sha'] != receipt_sha:
        raise ValueError('Build and collector commit differ')
    if receipt['validation'] != 'passed' or receipt['builds'] != builds():
        raise ValueError('Build receipt failed or production bytes changed')
    if (output / 'transport-manifest.json').exists():
        raise ValueError('Transport attempt already recorded; use a new job')
    frozen_schedule = schedule(index)
    manifest = {'purpose': PURPOSE, 'eligible_for_main_study': False,
                'eligible_for_cloud_transport': True, 'allocation_index': index,
                'lock_sha256': lock_sha, 'git_sha': receipt_sha,
                'run_id': os.environ['GITHUB_RUN_ID'], 'run_attempt': '1',
                'started_utc': datetime.now(timezone.utc).isoformat(),
                'validation': 'running', 'schedule': frozen_schedule,
                'browser_executable_sha256': sha(chrome), 'adapter_injected_by_collector': False,
                'adapter_install_checks': [], 'preflight': [], 'network': 'unthrottled-loopback'}
    for name in ('lock.json', 'frozen-actions.json'):
        shutil.copy2(ROOT / 'experiments/cloud_replication_v1' / name, output / name)
    rows = []
    write(output / 'transport-manifest.json', manifest)
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
                for trial in frozen_schedule['trials']:
                    key = (trial['application'], trial['action'], trial['case_id'])
                    if key not in seen:
                        manifest['preflight'].append(delivery(trial)); seen.add(key)
                    if key[:2] not in warmed:
                        row = measured({**trial, 'cpu_rate': 1, 'cache': 'cold'}, capture=True)
                        manifest['preflight'].append({'warmup': key[:2], 'record': row})
                        if row['status'] != 'ok' or not row['correctness'] or row['errors'] or row['external_requests']:
                            raise ValueError('Warmup failed; evidence retained')
                        warmed.add(key[:2])
                with (output / 'measurements.jsonl').open('x') as stream:
                    for trial in frozen_schedule['trials']:
                        row = measured(trial); rows.append(row)
                        stream.write(json.dumps(row) + '\n'); stream.flush()
                        print(f'{len(rows)}/72 {trial["application"]} {trial["action"]}: {row["status"]}', flush=True)
            finally:
                browser.close()
        validate(rows, frozen_schedule, manifest['adapter_install_checks'])
        if builds() != receipt['builds']:
            raise ValueError('Production build changed during transport collection')
        if verify_lock() != lock_sha:
            raise ValueError('Prospective lock changed during collection')
        manifest['validation'] = 'passed'
    except Exception as error:
        manifest.update(validation='failed', failure=str(error))
        raise
    finally:
        manifest['observations'] = len(rows)
        manifest['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write(output / 'transport-manifest.json', manifest)
        checksums(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--chrome', type=Path, required=True)
    parser.add_argument('--allocation', type=int, required=True)
    args = parser.parse_args()
    collect(args.output.resolve(), args.chrome.resolve(), args.allocation)
