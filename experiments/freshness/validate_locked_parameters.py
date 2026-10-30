"""Validate complete held-out artifacts against immutable training locks."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import statistics
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from .allocation_design import AllocationDesign
from .locked_execution import (
    load_event_lock, load_locked_costs, load_time_lock, locked_unit_specs,
)
from .trace_generator import TraceDesign
from .validation_design import ValidationDesign


TIME_POLICIES = ('fixed-ttl', 'stale-while-revalidate')
EVENT_POLICIES = ('event-invalidate-with-repair', 'write-reactive')


@dataclass(frozen=True)
class _Source:
    key: str
    read_bytes: Callable[[], bytes]

    def json(self) -> Mapping:
        return json.loads(self.read_bytes().decode('utf-8'))


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
                raise ValueError('each validation archive must contain exactly one manifest')
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


def _sha256(source: _Source) -> str:
    return hashlib.sha256(source.read_bytes()).hexdigest()


def _confirmation(training_mean: float, values: list[float], margin: float) -> dict:
    validation_mean = statistics.fmean(values)
    increase = validation_mean - training_mean
    return {
        'training_mean_freshness_violation': training_mean,
        'validation_mean_freshness_violation': validation_mean,
        'validation_minus_training': increase,
        'maximum_allowed_increase': margin,
        'trace_units': len(values),
        'passed': increase <= margin + 1e-12,
    }


def validate(
    root: Path,
    *,
    package: Path = Path('experiments/freshness'),
    cost_lock_path: Path = Path(
        'data/training/freshness-costs-40982405656/locked_costs.json'
    ),
    time_lock_path: Path = Path(
        'data/training/freshness-time-candidates-40984591923/'
        'selected_time_parameters.json'
    ),
    event_lock_path: Path = Path(
        'data/training/freshness-event-candidates-41006126071-archives/'
        'selected_event_parameters.json'
    ),
) -> dict:
    allocation = AllocationDesign.load(package / 'allocation_design_v1.json')
    trace_design = TraceDesign.load(package / 'trace_design_v1.json')
    design = ValidationDesign.load(
        package / 'validation_design_v1.json', trace_design, allocation,
    )
    costs = load_locked_costs(cost_lock_path)
    time_lock = load_time_lock(time_lock_path)
    event_lock = load_event_lock(event_lock_path)
    expected_lock_hashes = {
        'serialized_byte_costs': hashlib.sha256(cost_lock_path.read_bytes()).hexdigest(),
        'time_parameters': hashlib.sha256(time_lock_path.read_bytes()).hexdigest(),
        'event_parameters': hashlib.sha256(event_lock_path.read_bytes()).hexdigest(),
    }
    blocks = _filesystem_blocks(root)
    archives = []
    if not blocks:
        blocks, archives = _archive_blocks(root)
    if len(blocks) != design.expected_blocks:
        for archive in archives:
            archive.close()
        raise ValueError(
            f'validation requires exactly {design.expected_blocks} complete blocks'
        )
    seen = set()
    records = {}
    hashes = {}
    for block in blocks:
        manifest = block.manifest.json()
        if (
            not manifest.get('passed')
            or manifest.get('measurement_kind') != 'validation-locked-policy-block'
            or manifest.get('stage') != 'validation'
            or manifest.get('confirmatory_final_test') is not False
            or manifest.get('validation_design_sha256') != design.digest()
            or manifest.get('allocation_design_sha256') != allocation.digest()
            or manifest.get('parameter_lock_sha256') != expected_lock_hashes
        ):
            raise ValueError('validation contains a failed or identity-mismatched block')
        identity = manifest['block_identity']
        if not design.contains(identity):
            raise ValueError('validation block identity is outside the frozen design')
        key = (
            identity['workload'], identity['regime'], identity['fault_profile'],
            identity['transport'], identity['trace_seed'],
        )
        if key in seen:
            raise ValueError('duplicate validation block identity')
        seen.add(key)
        hashes[block.manifest.key] = _sha256(block.manifest)
        schedule = block.child('schedule.json')
        hashes[schedule.key] = _sha256(schedule)
        specs = {
            item.policy: dict(item.options)
            for item in locked_unit_specs(
                costs, time_lock, event_lock, identity['workload'], identity['regime'],
            )
        }
        attempts = manifest.get('attempts', ())
        if (
            len(attempts) != len(design.policies)
            or {item['policy'] for item in attempts} != set(design.policies)
            or any(item['returncode'] != 0 for item in attempts)
        ):
            raise ValueError('validation block does not contain eight successful policies')
        for attempt in attempts:
            options_source = block.child(attempt['options'])
            artifact_source = block.child(attempt['artifact'])
            hashes[options_source.key] = _sha256(options_source)
            hashes[artifact_source.key] = _sha256(artifact_source)
            policy = attempt['policy']
            options = options_source.json()
            artifact = artifact_source.json()
            if options != specs[policy] or artifact.get('policy_parameters') != specs[policy]:
                raise ValueError('validation policy options differ from the training lock')
            run = artifact.get('run', {})
            summary = artifact.get('summary', {})
            if (
                artifact.get('measurement_kind') != 'instrumented-freshness-trace-unit'
                or artifact.get('stage') != 'validation'
                or artifact.get('confirmatory_final_test') is not False
                or artifact.get('compact_raw_observations') is not True
                or artifact.get('workload_id') != identity['workload']
                or run.get('policy') != policy
                or run.get('schedule_sha256') != manifest['schedule_sha256']
                or run.get('trace_sha256') != manifest['trace_sha256']
                or run.get('fault_sha256') != manifest['fault_sha256']
                or summary.get('policy') != policy
                or summary.get('schedule_sha256') != manifest['schedule_sha256']
                or summary.get('trace_sha256') != manifest['trace_sha256']
                or summary.get('fault_sha256') != manifest['fault_sha256']
            ):
                raise ValueError('validation unit identity differs from its block')
            record_key = (identity['workload'], identity['regime'], policy)
            records.setdefault(record_key, {})[
                identity['fault_profile'], identity['transport'], identity['trace_seed']
            ] = summary['freshness_violation_proportion']
    expected_identities = set(itertools.product(
        design.workloads,
        design.regimes,
        design.fault_profiles,
        design.transports,
        range(design.seed_start, design.seed_start + design.seed_count),
    ))
    if seen != expected_identities:
        raise ValueError('validation campaign does not cover every frozen block identity')
    if len(hashes) != design.expected_blocks * (2 + 2 * len(design.policies)):
        raise ValueError('validation source-file count is incomplete')
    margin = design.source['confirmation_rule']['maximum_increase_over_training']
    checks = {}
    time_conditions = {
        (profile, transport, seed)
        for profile in design.source['time_policy_confirmation_condition']['fault_profiles']
        for transport in design.source['time_policy_confirmation_condition']['transports']
        for seed in range(design.seed_start, design.seed_start + design.seed_count)
    }
    event_conditions = {
        (profile, transport, seed)
        for profile in design.source['event_policy_confirmation_condition']['fault_profiles']
        for transport in design.source['event_policy_confirmation_condition']['transports']
        for seed in range(design.seed_start, design.seed_start + design.seed_count)
    }
    for workload in design.workloads:
        for regime in design.regimes:
            group = checks.setdefault(workload, {}).setdefault(regime, {})
            for policy in TIME_POLICIES:
                values = records[workload, regime, policy]
                if not time_conditions <= set(values):
                    raise ValueError('time-policy validation conditions are incomplete')
                group[policy] = _confirmation(
                    time_lock['selected'][workload][regime][policy][
                        'mean_freshness_violation'
                    ],
                    [values[condition] for condition in sorted(time_conditions)],
                    margin,
                )
            for policy in EVENT_POLICIES:
                values = records[workload, regime, policy]
                if not event_conditions <= set(values):
                    raise ValueError('event-policy validation conditions are incomplete')
                group[policy] = _confirmation(
                    event_lock['selected'][workload][regime][policy][
                        'mean_freshness_violation'
                    ],
                    [values[condition] for condition in sorted(event_conditions)],
                    margin,
                )
    passed = all(
        check['passed']
        for workloads in checks.values()
        for regimes in workloads.values()
        for check in regimes.values()
    )
    result = {
        'artifact_schema_version': 1,
        'measurement_kind': 'held-out-parameter-validation-report',
        'stage': 'validation',
        'confirmatory_final_test': False,
        'allow_refitting': False,
        'validation_design_sha256': design.digest(),
        'parameter_lock_sha256': expected_lock_hashes,
        'block_count': len(blocks),
        'full_trace_unit_count': len(blocks) * len(design.policies),
        'source_file_count': len(hashes),
        'checks': checks,
        'passed': passed,
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
    result = validate(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    if not result['passed']:
        raise SystemExit('held-out validation guardrail failed; see retained report')


if __name__ == '__main__':
    main()
