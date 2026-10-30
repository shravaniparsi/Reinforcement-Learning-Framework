"""Execute one held-out block with all eight policies and frozen options."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from .allocation_design import AllocationDesign
from .locked_execution import (
    load_event_lock, load_locked_costs, load_time_lock, locked_unit_specs,
)
from .schema import dump_schedule
from .trace_generator import TraceDesign, WORKLOAD_IDS, generate_schedule
from .validation_design import ValidationDesign
from .variance_design import VarianceDesign, load_passed_validation


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--stage', choices=('validation', 'variance-planning'), required=True)
    parser.add_argument('--workload', choices=WORKLOAD_IDS, required=True)
    parser.add_argument('--regime', required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--fault-profile', required=True)
    parser.add_argument('--transport', choices=('redis-pubsub', 'redis-streams'), required=True)
    parser.add_argument(
        '--cost-lock', type=Path,
        default=Path('data/training/freshness-costs-40982405656/locked_costs.json'),
    )
    parser.add_argument(
        '--time-lock', type=Path,
        default=Path(
            'data/training/freshness-time-candidates-40984591923/'
            'selected_time_parameters.json'
        ),
    )
    parser.add_argument(
        '--event-lock', type=Path,
        default=Path(
            'data/training/freshness-event-candidates-41006126071-archives/'
            'selected_event_parameters.json'
        ),
    )
    parser.add_argument(
        '--validation-lock', type=Path,
        default=Path(
            'data/validation/freshness-validation-41099780817-archives/'
            'validation_report.json'
        ),
    )
    args = parser.parse_args()
    package = Path(__file__).parent
    allocation = AllocationDesign.load(package / 'allocation_design_v1.json')
    trace_design = TraceDesign.load(package / 'trace_design_v1.json')
    if args.stage == 'validation':
        design = ValidationDesign.load(
            package / 'validation_design_v1.json', trace_design, allocation,
        )
        design_digest_key = 'validation_design_sha256'
        prerequisite = {}
    else:
        design = VarianceDesign.load(
            package / 'variance_design_v1.json', trace_design, allocation,
        )
        load_passed_validation(args.validation_lock)
        design_digest_key = 'variance_planning_design_sha256'
        prerequisite = {
            'prerequisite_validation_sha256': _sha256(args.validation_lock),
        }
    identity = {
        'stage': args.stage,
        'workload': args.workload,
        'regime': args.regime,
        'trace_seed': args.seed,
        'transport': args.transport,
        'fault_profile': args.fault_profile,
    }
    if not design.contains(identity):
        raise ValueError('block identity is outside the frozen collection campaign')
    costs = load_locked_costs(args.cost_lock)
    time_lock = load_time_lock(args.time_lock)
    event_lock = load_event_lock(args.event_lock)
    by_policy = {
        item.policy: item
        for item in locked_unit_specs(costs, time_lock, event_lock, args.workload, args.regime)
    }
    specs = tuple(by_policy[policy] for policy in allocation.policy_order(identity))
    schedule = generate_schedule(
        trace_design,
        workload_id=args.workload,
        regime=args.regime,
        partition=args.stage,
        seed=args.seed,
        fault_profile=args.fault_profile,
        transport_mode=args.transport,
    )
    args.output.mkdir(parents=True, exist_ok=False)
    schedule_path = args.output / 'schedule.json'
    dump_schedule(schedule, str(schedule_path))
    options_directory = args.output / 'options'
    options_directory.mkdir()
    attempts = []
    for position, spec in enumerate(specs):
        stem = '%03d-%s' % (position, spec.policy)
        options_path = options_directory / (stem + '.json')
        options_path.write_text(
            json.dumps(spec.options, indent=2, sort_keys=True, allow_nan=False) + '\n',
            encoding='utf-8',
        )
        artifact = args.output / (stem + '.json')
        completed = subprocess.run(
            [
                sys.executable, '-m', 'experiments.freshness.run_instrumented_unit',
                str(schedule_path), spec.policy, str(artifact), '--stage', args.stage,
                '--options-file', str(options_path), '--compact',
            ],
            text=True,
            capture_output=True,
        )
        attempts.append({
            'position': position,
            'unit_id': spec.unit_id,
            'policy': spec.policy,
            'returncode': completed.returncode,
            'stdout': completed.stdout,
            'stderr': completed.stderr,
            'artifact': artifact.name,
            'options': str(options_path.relative_to(args.output)),
        })
        if completed.returncode != 0:
            break
    passed = len(attempts) == len(specs) and all(item['returncode'] == 0 for item in attempts)
    manifest = {
        'artifact_schema_version': 1,
        'measurement_kind': f'{args.stage}-locked-policy-block',
        'stage': args.stage,
        'confirmatory_final_test': False,
        design_digest_key: design.digest(),
        **prerequisite,
        'allocation_design_sha256': allocation.digest(),
        'parameter_lock_sha256': {
            'serialized_byte_costs': _sha256(args.cost_lock),
            'time_parameters': _sha256(args.time_lock),
            'event_parameters': _sha256(args.event_lock),
        },
        'block_identity': identity,
        'family_order': list(allocation.policy_order(identity)),
        'unit_order': [item.unit_id for item in specs],
        'schedule_sha256': schedule.digest(),
        'trace_sha256': schedule.trace_digest(),
        'fault_sha256': schedule.fault_digest(),
        'attempts': attempts,
        'passed': passed,
    }
    with (args.output / 'manifest.json').open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    if not passed:
        raise SystemExit('validation block failed; see retained manifest')


if __name__ == '__main__':
    main()
