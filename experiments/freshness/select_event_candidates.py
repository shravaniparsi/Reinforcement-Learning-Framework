"""Select repair and write-reactive parameters from complete training units."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from .analysis_plan import CandidateSummary, select_candidate


EXPECTED_PROFILES = ('no-fault', 'delay-100ms', 'loss-10pct', 'combined-stress')
EXPECTED_TRANSPORTS = ('redis-pubsub', 'redis-streams')


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select(root: Path) -> dict:
    manifests = sorted(root.rglob('manifest.json'))
    if len(manifests) != 720:
        raise ValueError('event-candidate selection requires exactly 720 blocks')
    seen_blocks = set()
    records = {}
    hashes = {}
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if (
            not manifest.get('passed')
            or manifest.get('stage') != 'training'
            or manifest.get('phase') != 'event-candidates'
            or manifest.get('confirmatory_final_test') is not False
        ):
            raise ValueError('selection contains a failed or invalid event block')
        identity = manifest['block_identity']
        block_key = (
            identity['workload'], identity['regime'], identity['fault_profile'],
            identity['transport'], identity['trace_seed'],
        )
        if block_key in seen_blocks:
            raise ValueError('duplicate event-candidate block identity')
        seen_blocks.add(block_key)
        directory = manifest_path.parent
        for source in (manifest_path, directory / 'schedule.json'):
            hashes[str(source.relative_to(root))] = _sha256(source)
        if len(manifest['attempts']) != 18:
            raise ValueError('event-candidate block must contain 18 complete units')
        for attempt in manifest['attempts']:
            for source in (directory / attempt['artifact'], directory / attempt['options']):
                hashes[str(source.relative_to(root))] = _sha256(source)
        candidates = [attempt for attempt in manifest['attempts'] if attempt['candidate']]
        if len(candidates) != 12:
            raise ValueError('event-candidate block must contain 12 candidates')
        for attempt in candidates:
            artifact_path = directory / attempt['artifact']
            artifact = json.loads(artifact_path.read_text(encoding='utf-8'))
            if artifact['run']['trace_sha256'] != manifest['trace_sha256']:
                raise ValueError('event candidate trace identity differs from its block')
            summary = artifact['summary']
            key = (identity['workload'], identity['regime'], attempt['policy'], attempt['unit_id'])
            group = records.setdefault(key, {
                'units': set(), 'violations': [], 'origin_bytes': [],
                'declared_order': attempt['declared_order'],
                'options': artifact['policy_parameters'],
            })
            unit_key = (
                identity['fault_profile'], identity['transport'], identity['trace_seed'],
            )
            if unit_key in group['units']:
                raise ValueError('duplicate candidate condition/transport/seed unit')
            group['units'].add(unit_key)
            group['violations'].append(summary['freshness_violation_proportion'])
            group['origin_bytes'].append(
                summary['origin_response_body_bytes']
                + summary['publisher_origin_response_body_bytes']
            )

    expected_units = {
        (profile, transport, seed)
        for profile in EXPECTED_PROFILES
        for transport in EXPECTED_TRANSPORTS
        for seed in range(100, 110)
    }
    selected = {}
    grouped = {}
    for (workload, regime, policy, candidate_id), value in records.items():
        if value['units'] != expected_units:
            raise ValueError('event candidate does not contain all 80 training units')
        grouped.setdefault((workload, regime, policy), []).append((candidate_id, value))
    for (workload, regime, policy), candidates in sorted(grouped.items()):
        if len(candidates) != 6:
            raise ValueError('event candidate family is incomplete')
        summaries = [
            CandidateSummary(
                name=candidate_id,
                mean_freshness_violation=statistics.fmean(value['violations']),
                mean_origin_response_bytes=statistics.fmean(value['origin_bytes']),
                declared_order=value['declared_order'],
            )
            for candidate_id, value in candidates
        ]
        choice = select_candidate(summaries)
        chosen_value = dict(candidates)[choice.name]
        selected.setdefault(workload, {}).setdefault(regime, {})[policy] = {
            'candidate_id': choice.name,
            'options': chosen_value['options'],
            'mean_freshness_violation': choice.mean_freshness_violation,
            'mean_origin_response_bytes_including_publisher': choice.mean_origin_response_bytes,
            'trace_units': 80,
            'declared_order': choice.declared_order,
            'candidate_count': 6,
        }
    if len(selected) != 3 or any(len(regimes) != 3 for regimes in selected.values()):
        raise ValueError('event selection does not cover all workload/regime groups')
    return {
        'artifact_schema_version': 1,
        'measurement_kind': 'training-event-parameter-lock',
        'stage': 'training',
        'confirmatory_final_test': False,
        'independent_unit': 'full trace execution',
        'fitting_fault_profiles': list(EXPECTED_PROFILES),
        'fitting_transports': list(EXPECTED_TRANSPORTS),
        'selection_rule': (
            'minimum mean trace freshness violation; within 0.01 choose minimum '
            'mean request-plus-publisher origin response bytes; then declared order'
        ),
        'selected': selected,
        'source_artifact_sha256': hashes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = select(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
