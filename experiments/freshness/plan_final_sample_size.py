"""Lock final-test seed count from complete variance-planning artifacts."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import statistics
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from .allocation_design import AllocationDesign
from .analysis_plan import required_trace_count, reserved_pool_is_sufficient
from .locked_execution import (
    load_event_lock, load_locked_costs, load_time_lock, locked_unit_specs,
)
from .trace_generator import TraceDesign
from .variance_design import VarianceDesign, load_passed_validation


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
                raise ValueError('each variance archive must contain exactly one manifest')
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


def _outcome_value(summary: Mapping, outcome_id: str) -> float:
    if outcome_id == 'freshness_violation_proportion':
        value = summary[outcome_id]
    elif outcome_id == 'mean_request_wall_ns':
        value = summary['request_wall_ns']['mean']
    elif outcome_id == 'operation_thread_cpu_ns':
        value = summary[outcome_id]
    elif outcome_id == 'total_origin_response_body_bytes':
        value = (
            summary['origin_response_body_bytes']
            + summary['publisher_origin_response_body_bytes']
        )
    elif outcome_id == 'redis_delivery_payload_bytes':
        value = summary[outcome_id]
    else:
        raise ValueError(f'unsupported precision outcome: {outcome_id}')
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError('precision outcome must be finite and non-negative')
    return value


def _precision_calculation(
    treatment_values: Sequence[float],
    reference_values: Sequence[float],
    outcome: Mapping,
) -> dict:
    if len(treatment_values) != len(reference_values) or len(treatment_values) < 2:
        raise ValueError('precision planning requires complete paired trace values')
    treatment = tuple(float(value) for value in treatment_values)
    reference = tuple(float(value) for value in reference_values)
    differences = tuple(left - right for left, right in zip(treatment, reference))
    reference_mean = statistics.fmean(reference)
    if outcome['target_kind'] == 'absolute':
        target = float(outcome['target_value'])
    elif outcome['target_kind'] == 'reference_fraction':
        if reference_mean <= 0:
            raise ValueError('relative precision target requires a positive reference mean')
        target = float(outcome['target_value']) * reference_mean
    else:
        raise ValueError('unknown precision-target kind')
    return {
        'planning_trace_units': len(differences),
        'paired_mean_difference': statistics.fmean(differences),
        'paired_standard_deviation': statistics.stdev(differences),
        'reference_mean': reference_mean,
        'target_half_width': target,
        'required_final_seeds': required_trace_count(differences, target),
    }


def plan(
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
) -> dict:
    allocation = AllocationDesign.load(package / 'allocation_design_v1.json')
    trace_design = TraceDesign.load(package / 'trace_design_v1.json')
    design = VarianceDesign.load(
        package / 'variance_design_v1.json', trace_design, allocation,
    )
    costs = load_locked_costs(cost_lock_path)
    time_lock = load_time_lock(time_lock_path)
    event_lock = load_event_lock(event_lock_path)
    load_passed_validation(validation_lock_path)
    validation_lock_sha256 = hashlib.sha256(validation_lock_path.read_bytes()).hexdigest()
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
            f'variance planning requires exactly {design.expected_blocks} complete blocks'
        )
    seen = set()
    summaries = {}
    hashes = {}
    for block in blocks:
        manifest = block.manifest.json()
        if (
            not manifest.get('passed')
            or manifest.get('measurement_kind') != 'variance-planning-locked-policy-block'
            or manifest.get('stage') != 'variance-planning'
            or manifest.get('confirmatory_final_test') is not False
            or manifest.get('variance_planning_design_sha256') != design.digest()
            or manifest.get('prerequisite_validation_sha256') != validation_lock_sha256
            or manifest.get('allocation_design_sha256') != allocation.digest()
            or manifest.get('parameter_lock_sha256') != expected_lock_hashes
        ):
            raise ValueError('variance planning contains a failed or mismatched block')
        identity = manifest['block_identity']
        if not design.contains(identity):
            raise ValueError('variance block identity is outside the frozen design')
        block_key = (
            identity['workload'], identity['regime'], identity['fault_profile'],
            identity['transport'], identity['trace_seed'],
        )
        if block_key in seen:
            raise ValueError('duplicate variance block identity')
        seen.add(block_key)
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
            raise ValueError('variance block does not contain eight successful policies')
        for attempt in attempts:
            options_source = block.child(attempt['options'])
            artifact_source = block.child(attempt['artifact'])
            hashes[options_source.key] = _sha256(options_source)
            hashes[artifact_source.key] = _sha256(artifact_source)
            policy = attempt['policy']
            options = options_source.json()
            artifact = artifact_source.json()
            if options != specs[policy] or artifact.get('policy_parameters') != specs[policy]:
                raise ValueError('variance policy options differ from the training lock')
            run = artifact.get('run', {})
            summary = artifact.get('summary', {})
            if (
                artifact.get('measurement_kind') != 'instrumented-freshness-trace-unit'
                or artifact.get('stage') != 'variance-planning'
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
                raise ValueError('variance unit identity differs from its block')
            summary_key = (*block_key, policy)
            summaries[summary_key] = summary
    expected_identities = set(itertools.product(
        design.workloads,
        design.regimes,
        design.fault_profiles,
        design.transports,
        range(design.seed_start, design.seed_start + design.seed_count),
    ))
    if seen != expected_identities:
        raise ValueError('variance campaign does not cover every frozen block identity')
    if len(hashes) != design.expected_blocks * (2 + 2 * len(design.policies)):
        raise ValueError('variance source-file count is incomplete')
    calculations = []
    seeds = range(design.seed_start, design.seed_start + design.seed_count)
    for workload in design.workloads:
        for regime in design.regimes:
            for transport in design.transports:
                for contrast in design.source['primary_contrasts']:
                    fault = contrast['fault_profile']
                    treatment_summaries = [
                        summaries[
                            workload, regime, fault, transport, seed, contrast['treatment']
                        ]
                        for seed in seeds
                    ]
                    reference_summaries = [
                        summaries[
                            workload, regime, fault, transport, seed, contrast['reference']
                        ]
                        for seed in seeds
                    ]
                    for outcome in design.source['precision_outcomes']:
                        calculation = _precision_calculation(
                            [
                                _outcome_value(summary, outcome['outcome_id'])
                                for summary in treatment_summaries
                            ],
                            [
                                _outcome_value(summary, outcome['outcome_id'])
                                for summary in reference_summaries
                            ],
                            outcome,
                        )
                        calculations.append({
                            'workload': workload,
                            'regime': regime,
                            'transport': transport,
                            'contrast_id': contrast['contrast_id'],
                            'fault_profile': fault,
                            'treatment': contrast['treatment'],
                            'reference': contrast['reference'],
                            'outcome_id': outcome['outcome_id'],
                            **calculation,
                        })
    if len(calculations) != design.expected_precision_calculations:
        raise ValueError('variance precision calculations are incomplete')
    final_requirement = max(item['required_final_seeds'] for item in calculations)
    drivers = [
        item for item in calculations
        if item['required_final_seeds'] == final_requirement
    ]
    sufficient = reserved_pool_is_sufficient(final_requirement)
    result = {
        'artifact_schema_version': 1,
        'measurement_kind': 'final-test-sample-size-lock',
        'stage': 'variance-planning',
        'confirmatory_final_test': False,
        'allow_parameter_changes': False,
        'variance_planning_design_sha256': design.digest(),
        'parameter_lock_sha256': expected_lock_hashes,
        'prerequisite_validation_sha256': validation_lock_sha256,
        'independent_unit': 'one complete policy execution over one trace',
        'block_count': len(blocks),
        'full_trace_unit_count': len(blocks) * len(design.policies),
        'source_file_count': len(hashes),
        'precision_calculation_count': len(calculations),
        'planning_seeds_per_calculation': design.seed_count,
        'required_final_seeds': final_requirement,
        'reserved_final_seed_pool': design.source['precision_rule']['reserved_final_seeds'],
        'reserved_pool_sufficient': sufficient,
        'final_test_authorized': sufficient,
        'status': 'sample-size-locked' if sufficient else 'protocol-expansion-required',
        'requirement_drivers': drivers,
        'calculations': calculations,
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
    result = plan(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    if not result['reserved_pool_sufficient']:
        raise SystemExit('reserved final-test pool is insufficient; expand protocol')


if __name__ == '__main__':
    main()
