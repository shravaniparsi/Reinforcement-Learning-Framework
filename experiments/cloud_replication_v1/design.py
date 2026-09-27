"""Prospective fixed-budget hosted-runner transport design; no fitting."""
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments'))
from main_study_design import CASES

HERE = Path(__file__).resolve().parent
COUNT = 12
PURPOSE = 'cloud_frozen_policy_transport_v1'
POLICIES = ('always_ssr', 'always_csr', 'best_fixed', 'engineering_rule', 'context_table', 'ridge')
CELLS = tuple(f'{app}|{cpu}|{cache}' for app in CASES for cpu in (1, 4) for cache in ('cold', 'warm'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def schedule(index):
    if type(index) is not int or not 0 <= index < COUNT:
        raise ValueError('Allocation must be one of the 12 prospective indices')
    sid = f'cloud-v1-{index:02d}'
    seed = int(hashlib.sha256(f'cloud-transport-v1:20260926:{sid}'.encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    pairs = [(app, case, cpu, cache) for app, cases in CASES.items() for case in cases
             for cpu in (1, 4) for cache in ('cold', 'warm')]
    rng.shuffle(pairs)
    trials = []
    for pair_index, (app, case, cpu, cache) in enumerate(pairs):
        actions = ['ssr', 'csr']; rng.shuffle(actions)
        for action in actions:
            trials.append(dict(session_id=sid, stage='cloud_transport', index=len(trials),
                               pair_id=f'{sid}-pair-{pair_index:02d}', application=app,
                               **case, cpu_rate=cpu, cache=cache, action=action))
    return dict(session_id=sid, seed=seed, trials=trials)


def verify_lock(root=ROOT):
    lock = json.loads((root / 'experiments/cloud_replication_v1/lock.json').read_text())
    if lock['purpose'] != PURPOSE or not lock['files']:
        raise ValueError('Wrong or empty prospective lock')
    for name, expected in lock['files'].items():
        path = root / name
        if not path.is_file() or sha(path) != expected:
            raise ValueError(f'Locked source differs: {name}')
    frozen = json.loads((root / 'experiments/cloud_replication_v1/frozen-actions.json').read_text())
    if set(frozen['actions']) != set(POLICIES):
        raise ValueError('Missing frozen policies')
    for mapping in frozen['actions'].values():
        if set(mapping) != set(CELLS) or not set(mapping.values()) <= {'ssr', 'csr'}:
            raise ValueError('Invalid frozen action domain')
    return sha(root / 'experiments/cloud_replication_v1/lock.json')


if __name__ == '__main__':
    print('Verified prospective lock:', verify_lock())
