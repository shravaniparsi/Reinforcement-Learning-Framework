"""Functional reproducibility check only; deliberately does not report performance."""
import json
import shutil
import subprocess
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from browser_pilot import ROOT
from provenance import file_hash, run_directory

UPSTREAM = ROOT / 'experiments/vendor/svelte-realworld'
COMMIT = 'df796708040f5200ec572b28ab7f88ecee5794dd'
BASE = 'http://127.0.0.1:3105'


def expected(tag, page):
    ids = [i for i in range(29, -1, -1) if tag is None or i % 2 == (0 if tag == 'rendering' else 1)]
    return [{'title': f'Independent note {i:02d}', 'description': f'Local reproducibility fixture {i:02d}.',
             'href': f'/article/independent-note-{i}', 'tag': 'rendering' if i % 2 == 0 else 'accessibility'}
            for i in ids[(page - 1) * 10:page * 10]]


def verify(page, tag, number):
    wanted = expected(tag, number)
    page.wait_for_function('(title) => document.querySelector(".article-preview h1")?.textContent === title', arg=wanted[0]['title'])
    seen = page.locator('.article-preview').evaluate_all("""nodes => nodes.map(n => ({
       title: n.querySelector('h1').textContent, description: n.querySelector('.preview-link p').textContent,
       href: n.querySelector('.preview-link').getAttribute('href'), tag: n.querySelector('.tag-list li').textContent
    }))""")
    if seen != wanted:
        raise AssertionError(f'Unexpected content for {tag}, page {number}')
    return {'tag': tag, 'page': number, 'articles': len(seen), 'status': 'ok'}


def main():
    output = run_directory('external-realworld-smoke')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    revision = subprocess.check_output(['git', '-C', str(UPSTREAM), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != COMMIT:
        raise ValueError('Unexpected upstream commit')
    paths = [ROOT / p for p in ['experiments/external_realworld_backend.py', 'experiments/external_realworld_smoke.py',
              'experiments/external/svelte-realworld/README.md', 'experiments/external/svelte-realworld/local-fixture.patch',
              'experiments/external/svelte-realworld/LICENSE.upstream', 'requirements-research.lock.txt']]
    for path in paths:
        dest = output / 'source' / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    with (output / 'upstream.tar.gz').open('wb') as stream:
        subprocess.run(['git', '-C', str(UPSTREAM), 'archive', '--format=tar.gz', 'HEAD'], stdout=stream, check=True)
    actual_patch = subprocess.check_output(['git', '-C', str(UPSTREAM), 'diff'], text=True)
    if actual_patch != (ROOT / 'experiments/external/svelte-realworld/local-fixture.patch').read_text():
        raise AssertionError('Upstream changes differ from archived adaptation patch')
    checks, errors, external = [], [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=True)
        try:
            context = browser.new_context(viewport={'width': 1365, 'height': 900}, service_workers='block')
            def restrict(route):
                hostname = urlparse(route.request.url).hostname
                if hostname not in {'127.0.0.1', 'localhost', None}:
                    external.append(route.request.url)
                    route.abort()
                else:
                    route.continue_()
            context.route('**/*', restrict)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('requestfailed', lambda request: errors.append(f'{request.url}: {request.failure}'))
            page.on('response', lambda response: errors.append(f'HTTP {response.status}: {response.url}') if response.status >= 400 else None)
            for tag in [None, 'rendering', 'accessibility']:
                for number in [1, 2]:
                    url = BASE + f'/?page={number}' + (f'&tag={tag}' if tag else '')
                    with urlopen(url, timeout=10) as response:
                        html = response.read().decode()
                    wanted = expected(tag, number)
                    if f"<h1>{wanted[0]['title']}</h1>" not in html:
                        raise AssertionError('Article heading absent from SSR HTML')
                    response = page.goto(url)
                    if response.status != 200:
                        raise AssertionError('Navigation failed')
                    checks.append({**verify(page, tag, number), 'initial_html_verified': True})
            page.goto(BASE)
            verify(page, None, 1)
            page.wait_for_function("document.querySelector('.sidebar .tag-list a') !== null")
            page.locator('.sidebar .tag-list a', has_text='rendering').click()
            page.wait_for_url('**/?tag=rendering')
            checks.append({**verify(page, 'rendering', 1), 'interaction': 'tag-link'})
            page.locator('.pagination a', has_text='2').click()
            page.wait_for_url(lambda url: 'tag=rendering' in url and 'page=2' in url)
            checks.append({**verify(page, 'rendering', 2), 'interaction': 'pagination-link'})
            page.screenshot(path=str(output / 'smoke-check.png'), full_page=False)
            if external or errors:
                raise AssertionError(f'External requests: {external}; browser errors: {errors}')
            result = {'purpose': 'functional_external_app_reproducibility_only', 'upstream_url': 'https://github.com/sveltejs/realworld',
                      'upstream_commit': COMMIT, 'browser_version': browser.version, 'checks': checks,
                      'external_requests': external, 'errors': errors, 'performance_measurements': False,
                      'source_sha256': {str(p.relative_to(ROOT)): file_hash(p) for p in paths},
                      'upstream_archive_sha256': file_hash(output / 'upstream.tar.gz'),
                      'adapted_lock_sha256': file_hash(UPSTREAM / 'pnpm-lock.yaml')}
            (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
            print(f'{len(checks)} checks passed: {output}')
        except Exception as error:
            (output / 'failure.json').write_text(json.dumps({'error': str(error), 'checks': checks, 'errors': errors, 'external': external}, indent=2))
            raise
        finally:
            browser.close()


if __name__ == '__main__':
    main()
