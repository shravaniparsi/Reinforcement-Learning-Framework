"""Validate a complete cloud cohort before computing descriptive policy contrasts."""
import argparse
import json
import statistics
from pathlib import Path
from design import ROOT, HERE, COUNT, PURPOSE, POLICIES, CELLS, schedule, verify_lock, sha
from ci_engineering.run import validate, CHROME


def validate_cohort(entries, lock_sha):
    if len(entries) != COUNT:
        raise ValueError('Exactly 12 complete allocations required; no partial contrasts')
    seen, identities = set(), set()
    for manifest, receipt, rows in entries:
        index = manifest['allocation_index']
        if type(index) is not int or index in seen:
            raise ValueError('Duplicate or invalid allocation')
        expected = schedule(index)
        seen.add(index)
        if (manifest.get('purpose') != PURPOSE or manifest.get('validation') != 'passed'
                or manifest.get('eligible_for_cloud_transport') is not True
                or manifest.get('eligible_for_main_study') is not False
                or manifest.get('lock_sha256') != lock_sha
                or manifest.get('run_attempt') != '1'
                or manifest.get('schedule') != expected
                or manifest.get('browser_version') != CHROME
                or manifest.get('adapter_injected_by_collector') is not False
                or manifest.get('observations') != 72):
            raise ValueError('Ineligible transport manifest')
        if (receipt.get('validation') != 'passed' or receipt.get('git_sha') != manifest['git_sha']
                or receipt['runner']['GITHUB_RUN_ID'] != manifest['run_id']
                or receipt['runner']['GITHUB_RUN_ATTEMPT'] != '1'
                or receipt['runner']['RUNNER_ENVIRONMENT'] != 'github-hosted'):
            raise ValueError('Build/workflow provenance differs')
        identities.add((manifest['run_id'], manifest['git_sha'], manifest['browser_executable_sha256']))
        validate(rows, expected, manifest['adapter_install_checks'])
    if seen != set(range(COUNT)) or len(identities) != 1:
        raise ValueError('Mixed or incomplete workflow cohort')


def summarize(entries, actions):
    allocations = []
    for manifest, _, rows in sorted(entries, key=lambda e: e[0]['allocation_index']):
        groups = {c: {a: [] for a in ('ssr', 'csr')} for c in CELLS}
        for row in rows:
            cell = f'{row["application"]}|{row["cpu_rate"]}|{row["cache"]}'
            groups[cell][row['action']].append(row['metrics']['mount_hydration_ms'])
        if any(len(values) != 3 for cell in groups.values() for values in cell.values()):
            raise ValueError('Cell/action count differs')
        cells = {c: {a: statistics.mean(v) for a, v in values.items()} for c, values in groups.items()}
        scores = {p: statistics.mean(cells[c][actions[p][c]] for c in CELLS) for p in POLICIES}
        allocations.append({'allocation_index': manifest['allocation_index'],
                            'utc_start_date': manifest['started_utc'][:10], 'cell_action_ms': cells,
                            'policy_ms': scores,
                            'context_minus_fixed_ms': scores['context_table'] - scores['best_fixed']})
    means = {p: statistics.mean(a['policy_ms'][p] for a in allocations) for p in POLICIES}
    differences = [a['context_minus_fixed_ms'] for a in allocations]
    cells = {c: {action: statistics.mean(a['cell_action_ms'][c][action] for a in allocations)
                 for action in ('ssr', 'csr')} for c in CELLS}
    for c in CELLS:
        cells[c]['context_minus_fixed_ms'] = cells[c][actions['context_table'][c]] - cells[c][actions['best_fixed'][c]]
    date_groups = {}
    for a in allocations:
        date_groups.setdefault(a['utc_start_date'], []).append(a['context_minus_fixed_ms'])
    mean = statistics.mean(differences)
    return {'purpose': PURPOSE, 'inference': 'descriptive only; no confidence interval or p-value',
            'allocations': allocations, 'policy_mean_ms': means, 'cell_results': cells,
            'contrast_ms': {'mean': mean, 'median': statistics.median(differences),
                            'minimum': min(differences), 'maximum': max(differences)},
            'sign_counts': {'negative': sum(d < 0 for d in differences), 'zero': sum(d == 0 for d in differences),
                            'positive': sum(d > 0 for d in differences)},
            'direction': 'agreement' if mean < 0 else 'reversal' if mean > 0 else 'no mean difference',
            'relative_reduction_percent': 100 * (means['best_fixed'] - means['context_table']) / means['best_fixed']
                if means['best_fixed'] else None,
            'utc_start_dates': {d: {'allocations': len(v), 'mean_contrast_ms': statistics.mean(v)}
                                for d, v in sorted(date_groups.items())}}


def load(directory):
    # Reject traversal and require each retained file to be listed exactly once.
    listed = set()
    for line in (directory / 'checksums.sha256').read_text().splitlines():
        expected, name = line.split('  ', 1)
        path = directory / name
        if Path(name).is_absolute() or '..' in Path(name).parts or name in listed:
            raise ValueError('Invalid checksum path')
        listed.add(name)
        if sha(path) != expected:
            raise ValueError(f'Artifact hash differs: {name}')
    actual = {str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file() and p.name != 'checksums.sha256'}
    if listed != actual:
        raise ValueError('Artifact file inventory differs')
    manifest = json.loads((directory / 'transport-manifest.json').read_text())
    receipt = json.loads((directory / 'build-manifest.json').read_text())
    rows = [json.loads(line) for line in (directory / 'measurements.jsonl').read_text().splitlines()]
    return manifest, receipt, rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allocations', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    lock_sha = verify_lock()
    if len({p.resolve() for p in args.allocations}) != COUNT:
        raise ValueError('12 distinct artifact directories required')
    entries = [load(p) for p in args.allocations]
    validate_cohort(entries, lock_sha)
    result = summarize(entries, json.loads((HERE / 'frozen-actions.json').read_text())['actions'])
    result.update(lock_sha256=lock_sha, run_id=entries[0][0]['run_id'], git_sha=entries[0][0]['git_sha'],
                  provenance=[{'directory': str(p.resolve()),
                               'manifest_sha256': sha(p/'transport-manifest.json'),
                               'measurements_sha256': sha(p/'measurements.jsonl')} for p in args.allocations])
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(f'Validated 12 allocations; descriptive report saved: {args.output}')
