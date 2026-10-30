"""Lock serialized-byte costs from complete training calibration blocks."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(root: Path) -> dict:
    manifests = sorted(root.rglob('manifest.json'))
    if len(manifests) != 90:
        raise ValueError('cost calibration requires exactly 90 complete blocks')
    groups = {}
    source_hashes = {}
    seen = set()
    blocks = []
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if not manifest.get('passed') or manifest.get('stage') != 'training':
            raise ValueError('cost calibration contains a failed or non-training block')
        identity = manifest['block_identity']
        block_key = (identity['workload'], identity['regime'], identity['trace_seed'])
        if block_key in seen:
            raise ValueError('duplicate cost-calibration block identity')
        seen.add(block_key)
        blocks.append((manifest_path, manifest, identity))

    for manifest_path, manifest, identity in blocks:
        values = groups.setdefault((identity['workload'], identity['regime']), {
            'update': [], 'invalidate': [], 'miss': [], 'seeds': [],
        })
        values['seeds'].append(identity['trace_seed'])
        directory = manifest_path.parent
        schedule_path = directory / 'schedule.json'
        source_hashes[str(manifest_path.relative_to(root))] = _sha256(manifest_path)
        source_hashes[str(schedule_path.relative_to(root))] = _sha256(schedule_path)
        artifacts = {}
        for attempt in manifest['attempts']:
            path = directory / attempt['artifact']
            value = json.loads(path.read_text(encoding='utf-8'))
            artifacts[value['run']['policy']] = value
            source_hashes[str(path.relative_to(root))] = _sha256(path)
        for delivery in artifacts['always-update']['run']['transport_deliveries']:
            values['update'].append(delivery['payload_bytes'])
        for delivery in artifacts['always-invalidate']['run']['transport_deliveries']:
            values['invalidate'].append(delivery['payload_bytes'])
        for observation in artifacts['bypass']['run']['observations']:
            if observation['origin_operation'] == 'fetch':
                values['miss'].append(observation['origin_response_body_bytes'])
    expected_seeds = list(range(100, 110))
    locked = {}
    for (workload, regime), values in sorted(groups.items()):
        if sorted(values['seeds']) != expected_seeds:
            raise ValueError('cost group does not contain all ten training seeds')
        if not all(values[name] for name in ('update', 'invalidate', 'miss')):
            raise ValueError('cost group contains an empty byte distribution')
        locked.setdefault(workload, {})[regime] = {
            'update_cost_bytes': statistics.median(values['update']),
            'invalidate_cost_bytes': statistics.median(values['invalidate']),
            'miss_cost_bytes': statistics.median(values['miss']),
            'update_observations': len(values['update']),
            'invalidate_observations': len(values['invalidate']),
            'miss_observations': len(values['miss']),
            'trace_units_per_policy': 10,
        }
    return {
        'artifact_schema_version': 1,
        'measurement_kind': 'training-serialized-byte-cost-lock',
        'stage': 'training',
        'confirmatory_final_test': False,
        'independent_unit_for_policy_comparisons': 'full trace execution',
        'cost_observation': 'serialized delivered message or origin-miss response',
        'summary_statistic': 'median serialized bytes by workload and regime',
        'costs': locked,
        'source_artifact_sha256': source_hashes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = summarize(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
