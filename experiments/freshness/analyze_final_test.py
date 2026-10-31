"""Produce the frozen confirmatory analysis from complete final-test artifacts."""

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
from .analysis_plan import paired_bootstrap_mean_interval
from .final_design import FinalDesign, load_sample_size_lock
from .locked_execution import (
    load_event_lock, load_locked_costs, load_time_lock, locked_unit_specs,
)
from .plan_final_sample_size import _outcome_value
from .trace_generator import TraceDesign, generate_schedule
from .variance_design import load_passed_validation


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
                raise ValueError('each final archive must contain exactly one manifest')
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


def _bootstrap_seed(identity: Mapping) -> int:
    encoded = json.dumps(
        identity, sort_keys=True, separators=(',', ':'), allow_nan=False,
    ).encode('utf-8')
    return int.from_bytes(hashlib.sha256(encoded).digest()[:8], 'big')


def _estimate(
    treatment: Mapping[int, float],
    reference: Mapping[int, float],
    identity: Mapping,
) -> dict:
    if set(treatment) != set(reference) or len(treatment) != 67:
        raise ValueError('confirmatory estimate requires 67 complete paired traces')
    seeds = sorted(treatment)
    differences = [treatment[seed] - reference[seed] for seed in seeds]
    interval = paired_bootstrap_mean_interval(
        differences,
        confidence=0.99,
        resamples=10_000,
        seed=_bootstrap_seed(identity),
    )
    ratios = [
        treatment[seed] / reference[seed]
        for seed in seeds
        if reference[seed] > 0
    ]
    return {
        'estimate': interval.estimate,
        'lower': interval.lower,
        'upper': interval.upper,
        'confidence': interval.confidence,
        'n': interval.n,
        'resamples': interval.resamples,
        'consistent_negative_count': sum(value < 0 for value in differences),
        'consistent_positive_count': sum(value > 0 for value in differences),
        'zero_difference_count': sum(value == 0 for value in differences),
        'paired_mean_ratio': statistics.fmean(ratios) if len(ratios) == len(seeds) else None,
    }


def analyze(
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
    validation_lock_path: Path = Path(
        'data/validation/freshness-validation-41099780817-archives/'
        'validation_report.json'
    ),
    sample_size_lock_path: Path = Path(
        'data/variance/freshness-variance-41131844320-archives/'
        'final_sample_size_lock.json'
    ),
    protocol_path: Path = Path(
        'paper/followup/freshness-aware-caching/protocol/protocol_v0.5.md'
    ),
) -> dict:
    allocation = AllocationDesign.load(package / 'allocation_design_v1.json')
    trace_design = TraceDesign.load(package / 'trace_design_v2.json')
    sample_size_lock = load_sample_size_lock(sample_size_lock_path)
    design = FinalDesign.load(
        package / 'final_design_v1.json', trace_design, allocation, sample_size_lock,
    )
    load_passed_validation(validation_lock_path)
    costs = load_locked_costs(cost_lock_path)
    time_lock = load_time_lock(time_lock_path)
    event_lock = load_event_lock(event_lock_path)
    expected_lock_hashes = {
        'serialized_byte_costs': hashlib.sha256(cost_lock_path.read_bytes()).hexdigest(),
        'time_parameters': hashlib.sha256(time_lock_path.read_bytes()).hexdigest(),
        'event_parameters': hashlib.sha256(event_lock_path.read_bytes()).hexdigest(),
    }
    expected_protocol_hash = hashlib.sha256(protocol_path.read_bytes()).hexdigest()
    expected_validation_hash = hashlib.sha256(validation_lock_path.read_bytes()).hexdigest()
    expected_sample_hash = hashlib.sha256(sample_size_lock_path.read_bytes()).hexdigest()
    expected_source_hashes = {
        name: hashlib.sha256((package / name).read_bytes()).hexdigest()
        for name in (
            'run_final_block.py', 'final_design.py', 'run_instrumented_unit.py',
            'measurement.py', 'redis_delivery.py', 'cache_gateway.py', 'trace_runner.py',
        )
    }
    expected_unit_source_hashes = {
        name: digest for name, digest in expected_source_hashes.items()
        if name not in {'run_final_block.py', 'final_design.py'}
    }
    blocks = _filesystem_blocks(root)
    archives = []
    if not blocks:
        blocks, archives = _archive_blocks(root)
    if len(blocks) != design.expected_blocks:
        for archive in archives:
            archive.close()
        raise ValueError(f'final analysis requires exactly {design.expected_blocks} blocks')
    seen = set()
    summaries = {}
    hashes = {}
    for block in blocks:
        manifest = block.manifest.json()
        if (
            not manifest.get('passed')
            or manifest.get('measurement_kind') != 'confirmatory-final-test-block'
            or manifest.get('stage') != 'final-test'
            or manifest.get('confirmatory_final_test') is not True
            or manifest.get('protocol') != 'freshness-protocol-v0.5'
            or manifest.get('protocol_sha256') != expected_protocol_hash
            or manifest.get('final_design_sha256') != design.digest()
            or manifest.get('trace_design_sha256') != trace_design.digest()
            or manifest.get('allocation_design_sha256') != allocation.digest()
            or manifest.get('prerequisite_validation_sha256') != expected_validation_hash
            or manifest.get('sample_size_lock_sha256') != expected_sample_hash
            or manifest.get('parameter_lock_sha256') != expected_lock_hashes
            or manifest.get('source_sha256') != expected_source_hashes
        ):
            raise ValueError('final analysis contains a failed or mismatched block')
        identity = manifest['block_identity']
        if not design.contains(identity):
            raise ValueError('final block identity is outside the frozen design')
        block_key = (
            identity['workload'], identity['regime'], identity['fault_profile'],
            identity['transport'], identity['trace_seed'],
        )
        if block_key in seen:
            raise ValueError('duplicate final block identity')
        seen.add(block_key)
        hashes[block.manifest.key] = _sha256(block.manifest)
        schedule = block.child('schedule.json')
        hashes[schedule.key] = _sha256(schedule)
        expected_schedule = generate_schedule(
            trace_design,
            workload_id=identity['workload'],
            regime=identity['regime'],
            partition='final-test',
            seed=identity['trace_seed'],
            fault_profile=identity['fault_profile'],
            transport_mode=identity['transport'],
        )
        if (
            schedule.json() != expected_schedule.to_mapping()
            or manifest.get('schedule_sha256') != expected_schedule.digest()
            or manifest.get('trace_sha256') != expected_schedule.trace_digest()
            or manifest.get('fault_sha256') != expected_schedule.fault_digest()
        ):
            raise ValueError('final schedule differs from the frozen generator')
        locked_specs = locked_unit_specs(
            costs, time_lock, event_lock, identity['workload'], identity['regime'],
        )
        specs = {item.policy: dict(item.options) for item in locked_specs}
        unit_ids = {item.policy: item.unit_id for item in locked_specs}
        attempts = manifest.get('attempts', ())
        expected_order = allocation.policy_order(identity)
        if (
            len(attempts) != len(design.policies)
            or {item['policy'] for item in attempts} != set(design.policies)
            or any(item['returncode'] != 0 for item in attempts)
            or manifest.get('family_order') != list(expected_order)
            or [item['policy'] for item in attempts] != list(expected_order)
            or [item['position'] for item in attempts] != list(range(len(expected_order)))
            or manifest.get('unit_order') != [unit_ids[policy] for policy in expected_order]
        ):
            raise ValueError('final block does not contain eight successful policies')
        for attempt in attempts:
            options_source = block.child(attempt['options'])
            artifact_source = block.child(attempt['artifact'])
            hashes[options_source.key] = _sha256(options_source)
            hashes[artifact_source.key] = _sha256(artifact_source)
            policy = attempt['policy']
            artifact = artifact_source.json()
            if (
                options_source.json() != specs[policy]
                or artifact.get('policy_parameters') != specs[policy]
            ):
                raise ValueError('final policy options differ from the training lock')
            run = artifact.get('run', {})
            summary = artifact.get('summary', {})
            if (
                artifact.get('measurement_kind') != 'instrumented-freshness-trace-unit'
                or artifact.get('stage') != 'final-test'
                or artifact.get('confirmatory_final_test') is not True
                or artifact.get('protocol') != 'freshness-protocol-v0.5'
                or artifact.get('compact_raw_observations') is not True
                or artifact.get('workload_id') != identity['workload']
                or artifact.get('source_sha256') != {
                    'schedule': _sha256(schedule),
                    **expected_unit_source_hashes,
                }
                or run.get('policy') != policy
                or run.get('schedule_sha256') != manifest['schedule_sha256']
                or run.get('trace_sha256') != manifest['trace_sha256']
                or run.get('fault_sha256') != manifest['fault_sha256']
                or summary.get('policy') != policy
                or summary.get('schedule_sha256') != manifest['schedule_sha256']
                or summary.get('trace_sha256') != manifest['trace_sha256']
                or summary.get('fault_sha256') != manifest['fault_sha256']
            ):
                raise ValueError('final unit identity differs from its block')
            summaries[(*block_key, policy)] = summary
    expected_identities = set(itertools.product(
        design.workloads,
        design.regimes,
        design.fault_profiles,
        design.transports,
        range(design.seed_start, design.seed_start + design.seed_count),
    ))
    if seen != expected_identities:
        raise ValueError('final campaign does not cover every frozen block identity')
    if len(hashes) != design.expected_blocks * (2 + 2 * len(design.policies)):
        raise ValueError('final source-file count is incomplete')
    estimates = []
    seeds = range(design.seed_start, design.seed_start + design.seed_count)
    for workload in design.workloads:
        for regime in design.regimes:
            for transport in design.transports:
                for contrast in design.source['primary_contrasts']:
                    fault = contrast['fault_profile']
                    freshness_estimate = None
                    staged = []
                    for outcome_id in design.source['primary_outcomes']:
                        treatment = {
                            seed: _outcome_value(
                                summaries[
                                    workload, regime, fault, transport, seed,
                                    contrast['treatment'],
                                ],
                                outcome_id,
                            )
                            for seed in seeds
                        }
                        reference = {
                            seed: _outcome_value(
                                summaries[
                                    workload, regime, fault, transport, seed,
                                    contrast['reference'],
                                ],
                                outcome_id,
                            )
                            for seed in seeds
                        }
                        identity = {
                            'workload': workload,
                            'regime': regime,
                            'transport': transport,
                            'contrast_id': contrast['contrast_id'],
                            'outcome_id': outcome_id,
                        }
                        estimate = _estimate(treatment, reference, identity)
                        if outcome_id == 'freshness_violation_proportion':
                            freshness_estimate = estimate
                        staged.append((outcome_id, estimate))
                    if freshness_estimate is None:
                        raise ValueError('primary contrast lacks a freshness estimate')
                    admissible = freshness_estimate['upper'] <= 0.01
                    for outcome_id, estimate in staged:
                        estimates.append({
                            'workload': workload,
                            'regime': regime,
                            'transport': transport,
                            'contrast_id': contrast['contrast_id'],
                            'fault_profile': fault,
                            'treatment': contrast['treatment'],
                            'reference': contrast['reference'],
                            'outcome_id': outcome_id,
                            'efficiency_interpretation_authorized': (
                                True if outcome_id == 'freshness_violation_proportion'
                                else admissible
                            ),
                            **estimate,
                        })
    if len(estimates) != design.expected_primary_estimates:
        raise ValueError('final primary estimates are incomplete')
    result = {
        'artifact_schema_version': 1,
        'measurement_kind': 'confirmatory-final-analysis',
        'stage': 'final-test',
        'confirmatory_final_test': True,
        'protocol': 'freshness-protocol-v0.5',
        'protocol_sha256': expected_protocol_hash,
        'final_design_sha256': design.digest(),
        'trace_design_sha256': trace_design.digest(),
        'parameter_lock_sha256': expected_lock_hashes,
        'prerequisite_validation_sha256': expected_validation_hash,
        'sample_size_lock_sha256': expected_sample_hash,
        'independent_unit': design.source['analysis']['independent_unit'],
        'block_count': len(blocks),
        'full_trace_unit_count': len(blocks) * len(design.policies),
        'source_file_count': len(hashes),
        'primary_estimate_count': len(estimates),
        'p_values_reported': False,
        'simultaneous_familywise_coverage_claim': False,
        'primary_estimates': estimates,
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
    result = analyze(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
