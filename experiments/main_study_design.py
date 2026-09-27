"""Prospective schedule and fail-closed collection gate; no browser dependencies."""
import hashlib
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COUNTS = {'training': 8, 'validation': 4, 'variance': 6}
CASES = {
    'catalog': [{'case_id': f'catalog-repeat-{i}', 'repetition': i} for i in range(3)],
    'articles': [{'case_id': f'{tag}-{offset}', 'repetition': i, 'tag': tag, 'offset': offset}
                 for i, (tag, offset) in enumerate([('rendering', 0), ('accessibility', 20), ('rendering', 40)])],
    'external': [{'case_id': tag or 'all', 'repetition': i, 'tag': tag}
                 for i, tag in enumerate([None, 'rendering', 'accessibility'])],
}

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def session_schedule(stage, index):
    if stage not in {'engineering', *COUNTS}:
        raise ValueError('Test schedule requires the future variance-derived launch lock; not available yet')
    if type(index) is not int or not 0 <= index < COUNTS.get(stage, 1):
        raise ValueError('Session index outside predeclared stage')
    session_id = f'{stage}-{index:02d}'
    seed = int(hashlib.sha256(f'main-v1:20260918:{session_id}'.encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    pairs = [(app, case, cpu, cache) for app, cases in CASES.items() for case in cases
             for cpu in [1, 4] for cache in ['cold', 'warm']]
    rng.shuffle(pairs)
    trials = []
    for pair_index, (app, case, cpu, cache) in enumerate(pairs):
        actions = ['ssr', 'csr']; rng.shuffle(actions)
        for action in actions:
            trials.append({'session_id': session_id, 'stage': stage, 'index': len(trials),
                           'pair_id': f'{session_id}-pair-{pair_index:02d}', 'application': app,
                           **case, 'cpu_rate': cpu, 'cache': cache, 'action': action})
    return {'session_id': session_id, 'seed': seed, 'trials': trials}

def design_manifest():
    return {'schema_version': 1, 'purpose': 'prospective schedule; not launch authorization',
            'network': 'unthrottled-loopback', 'cases': CASES,
            'catalog_repetitions': 'Same immutable catalog repeated three times; not distinct workloads',
            'stages': {stage: [session_schedule(stage, i) for i in range(count)] for stage, count in COUNTS.items()},
            'test': {'status': 'blocked_until_policy_freeze_and_variance_rule', 'sessions': []},
            'collection_enabled': ['engineering'],
            'blocked_on': ['common primary measurement contract', 'policy fitting and freeze',
                           'stage completion validation', 'variance-derived N', 'final source/configuration lock']}

def authorize_collection(stage):
    if stage != 'engineering':
        raise ValueError('Main-study collection is disabled: readiness/policy/analysis launch gates remain open')

def validate_session(rows, schedule):
    expected = schedule['trials']
    if len(rows) != len(expected):
        raise ValueError('Incomplete session; missing trials cannot be dropped')
    for row, trial in zip(rows, expected):
        if any(row.get(key) != value for key, value in trial.items()):
            raise ValueError('Record identity/order differs from frozen schedule')
        if row.get('status') != 'ok' or row.get('correctness') is not True:
            raise ValueError('Invalid observation retained: session cannot pass the completeness gate')
        value = (row.get('metrics') or {}).get('mount_hydration_ms')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError('Missing/nonfinite timing cannot pass as a successful observation')
    for index in range(0, len(rows), 2):
        if not rows[index].get('content_sha256') or rows[index]['content_sha256'] != rows[index+1].get('content_sha256'):
            raise ValueError('Matched actions do not have equivalent content')
    return True

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = design_manifest()
    with args.output.open('x') as stream:
        json.dump(manifest, stream, indent=2); stream.write('\n')
    print(f'Wrote prospective schedule: {args.output}; sha256(canonical JSON)={digest(manifest)}')
