"""Execute one prospective engineering or precision-planning extension block."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from .allocation_design import AllocationDesign
from .clustered_loss_design import ClusteredLossDesign, EXTENSION_PARTITIONS, generate_clustered_schedule
from .locked_execution import load_event_lock, load_locked_costs, load_time_lock, locked_unit_specs
from .schema import dump_schedule
from .trace_generator import TraceDesign, WORKLOAD_IDS


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--stage', choices=EXTENSION_PARTITIONS, required=True)
    parser.add_argument('--workload', choices=WORKLOAD_IDS, required=True)
    parser.add_argument('--regime', required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--fault-profile', required=True)
    parser.add_argument('--transport', choices=('redis-pubsub', 'redis-streams'), required=True)
    parser.add_argument('--cost-lock', type=Path, default=Path(
        'data/training/freshness-costs-40982405656/locked_costs.json'
    ))
    parser.add_argument('--time-lock', type=Path, default=Path(
        'data/training/freshness-time-candidates-40984591923/selected_time_parameters.json'
    ))
    parser.add_argument('--event-lock', type=Path, default=Path(
        'data/training/freshness-event-candidates-41006126071-archives/'
        'selected_event_parameters.json'
    ))
    args = parser.parse_args()

    package = Path(__file__).parent
    base = TraceDesign.load(package / 'trace_design_v2.json')
    design_path = package / 'clustered_loss_design_v1.json'
    design = ClusteredLossDesign.load(design_path, base)
    identity = {
        'stage': args.stage, 'workload': args.workload, 'regime': args.regime,
        'trace_seed': args.seed, 'fault_profile': args.fault_profile,
        'transport': args.transport,
    }
    if not design.contains(identity):
        raise ValueError('block identity is outside the clustered-loss extension design')

    costs = load_locked_costs(args.cost_lock)
    time_lock = load_time_lock(args.time_lock)
    event_lock = load_event_lock(args.event_lock)
    by_policy = {
        item.policy: item
        for item in locked_unit_specs(costs, time_lock, event_lock, args.workload, args.regime)
    }
    policies = tuple(design.source['policies'])
    allocation = AllocationDesign.load(package / 'allocation_design_v1.json')
    ordered = [policy for policy in allocation.policy_order(identity) if policy in policies]
    if set(ordered) != set(policies):
        raise ValueError('counterbalanced order does not cover the extension policies')
    specs = tuple(by_policy[policy] for policy in ordered)
    schedule = generate_clustered_schedule(
        design, base,
        workload_id=args.workload, regime=args.regime, partition=args.stage,
        seed=args.seed, fault_profile=args.fault_profile, transport_mode=args.transport,
    )

    args.output.mkdir(parents=True, exist_ok=False)
    schedule_path = args.output / 'schedule.json'
    dump_schedule(schedule, str(schedule_path))
    options_directory = args.output / 'options'
    options_directory.mkdir()
    attempts = []
    for position, spec in enumerate(specs):
        stem = f'{position:03d}-{spec.policy}'
        options_path = options_directory / f'{stem}.json'
        options_path.write_text(
            json.dumps(spec.options, indent=2, sort_keys=True, allow_nan=False) + '\n',
            encoding='utf-8',
        )
        artifact = args.output / f'{stem}.json'
        completed = subprocess.run(
            [
                sys.executable, '-m', 'experiments.freshness.run_clustered_loss_unit',
                str(schedule_path), spec.policy, str(artifact), '--stage', args.stage,
                '--options-file', str(options_path), '--compact',
            ],
            text=True, capture_output=True,
        )
        attempts.append({
            'position': position, 'unit_id': spec.unit_id, 'policy': spec.policy,
            'returncode': completed.returncode, 'stdout': completed.stdout,
            'stderr': completed.stderr, 'artifact': artifact.name,
            'options': str(options_path.relative_to(args.output)),
        })
        if completed.returncode != 0:
            break
    passed = len(attempts) == len(specs) and all(item['returncode'] == 0 for item in attempts)
    manifest = {
        'artifact_schema_version': 1,
        'measurement_kind': f'{args.stage}-clustered-loss-block',
        'stage': args.stage,
        'confirmatory_final_test': False,
        'final_extension_collection': False,
        'protocol': 'clustered-loss-protocol-v0.1',
        'clustered_loss_design_sha256': design.digest(),
        'base_trace_design_sha256': base.digest(),
        'allocation_design_sha256': allocation.digest(),
        'parameter_lock_sha256': {
            'serialized_byte_costs': _sha256(args.cost_lock),
            'time_parameters': _sha256(args.time_lock),
            'event_parameters': _sha256(args.event_lock),
        },
        'block_identity': identity,
        'family_order': ordered,
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
        raise SystemExit('clustered-loss block failed; see retained manifest')


if __name__ == '__main__':
    main()
