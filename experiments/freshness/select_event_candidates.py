"""Select repair and write-reactive parameters from complete training units."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .analysis_plan import CandidateSummary, select_candidate


EXPECTED_PROFILES = ('no-fault', 'delay-100ms', 'loss-10pct', 'combined-stress')
EXPECTED_TRANSPORTS = ('redis-pubsub', 'redis-streams')


@dataclass(frozen=True)
class _Source:
    key: str
    read_bytes: Callable[[], bytes]

    def text(self) -> str:
        return self.read_bytes().decode('utf-8')


@dataclass(frozen=True)
class _Block:
    manifest: _Source
    child: Callable[[str], _Source]


def _filesystem_blocks(root: Path) -> list[_Block]:
    blocks = []
    for manifest_path in sorted(root.rglob('manifest.json')):
        directory = manifest_path.parent

        def child(relative: str, directory: Path = directory) -> _Source:
            source = directory / relative
            return _Source(str(source.relative_to(root)), source.read_bytes)

        blocks.append(_Block(child('manifest.json'), child))
    return blocks


def _archive_blocks(root: Path) -> tuple[list[_Block], list[zipfile.ZipFile]]:
    blocks = []
    archives = []
    try:
        for archive_path in sorted(root.glob('*.zip')):
            archive = zipfile.ZipFile(archive_path)
            archives.append(archive)
            manifests = [
                name for name in archive.namelist()
                if not name.endswith('/') and name.endswith('/manifest.json')
            ]
            if len(manifests) != 1:
                raise ValueError('each event archive must contain exactly one manifest')
            directory = manifests[0].rsplit('/', 1)[0]

            def child(
                relative: str,
                archive: zipfile.ZipFile = archive,
                directory: str = directory,
                archive_name: str = archive_path.stem,
            ) -> _Source:
                member = f'{directory}/{relative}'
                return _Source(f'{archive_name}/{member}', lambda: archive.read(member))

            blocks.append(_Block(child('manifest.json'), child))
    except Exception:
        for archive in archives:
            archive.close()
        raise
    return blocks, archives


def select(root: Path) -> dict:
    blocks = _filesystem_blocks(root)
    archives = []
    if not blocks:
        blocks, archives = _archive_blocks(root)
    if len(blocks) != 720:
        for archive in archives:
            archive.close()
        raise ValueError('event-candidate selection requires exactly 720 blocks')
    seen_blocks = set()
    records = {}
    hashes = {}
    for block in blocks:
        manifest = json.loads(block.manifest.text())
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
        for source in (block.manifest, block.child('schedule.json')):
            hashes[source.key] = hashlib.sha256(source.read_bytes()).hexdigest()
        if len(manifest['attempts']) != 18:
            raise ValueError('event-candidate block must contain 18 complete units')
        for attempt in manifest['attempts']:
            for source in (block.child(attempt['artifact']), block.child(attempt['options'])):
                hashes[source.key] = hashlib.sha256(source.read_bytes()).hexdigest()
        candidates = [attempt for attempt in manifest['attempts'] if attempt['candidate']]
        if len(candidates) != 12:
            raise ValueError('event-candidate block must contain 12 candidates')
        for attempt in candidates:
            artifact = json.loads(block.child(attempt['artifact']).text())
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
    result = {
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
    for archive in archives:
        archive.close()
    return result


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
