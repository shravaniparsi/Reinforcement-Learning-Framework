"""Execute one matched candidate-fitting block in isolated subprocesses."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from .allocation_design import AllocationDesign
from .schema import dump_schedule
from .trace_generator import TraceDesign, WORKLOAD_IDS, generate_schedule
from .training_campaign import TrainingCampaign
from .training_execution import load_locked_costs, load_time_lock, unit_specs


def _ordered_specs(allocation, identity, phase, specs):
    family_order = allocation.policy_order(identity)
    family_position = {policy: index for index, policy in enumerate(family_order)}

    def key(spec):
        encoded = json.dumps(
            {'identity': identity, 'phase': phase, 'unit_id': spec.unit_id},
            sort_keys=True, separators=(',', ':'), allow_nan=False,
        ).encode('utf-8')
        return family_position[spec.policy], hashlib.sha256(encoded).hexdigest()

    return tuple(sorted(specs, key=key))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--phase', choices=('time-candidates', 'event-candidates'), required=True)
    parser.add_argument('--workload', choices=WORKLOAD_IDS, required=True)
    parser.add_argument('--regime', required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--fault-profile', default='no-fault')
    parser.add_argument('--transport', choices=('redis-pubsub', 'redis-streams'), default='redis-pubsub')
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
    args = parser.parse_args()
    if args.phase == 'time-candidates' and (
        args.fault_profile != 'no-fault' or args.transport != 'redis-pubsub'
    ):
        raise ValueError('time candidates require the canonical no-fault Pub/Sub identity')

    package = Path(__file__).parent
    allocation = AllocationDesign.load(package / 'allocation_design_v1.json')
    trace_design = TraceDesign.load(package / 'trace_design_v1.json')
    campaign = TrainingCampaign.load(
        package / 'training_campaign_v1.json',
        package / 'parameter_grid_v1.json',
        package / 'trace_design_v1.json',
    )
    costs = load_locked_costs(args.cost_lock)
    time_lock = load_time_lock(args.time_lock) if args.phase == 'event-candidates' else None
    identity = {
        'stage': 'training',
        'workload': args.workload,
        'regime': args.regime,
        'trace_seed': args.seed,
        'transport': args.transport,
        'fault_profile': args.fault_profile,
    }
    specs = _ordered_specs(
        allocation, identity, args.phase,
        unit_specs(
            campaign, costs, args.phase, args.workload, args.regime,
            time_lock=time_lock,
        ),
    )
    schedule = generate_schedule(
        trace_design,
        workload_id=args.workload,
        regime=args.regime,
        partition='training',
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
                str(schedule_path), spec.policy, str(artifact), '--stage', 'training',
                '--options-file', str(options_path), '--compact',
            ],
            text=True,
            capture_output=True,
        )
        attempts.append({
            'position': position,
            'unit_id': spec.unit_id,
            'policy': spec.policy,
            'candidate': spec.candidate,
            'declared_order': spec.declared_order,
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
        'measurement_kind': 'training-candidate-block',
        'stage': 'training',
        'phase': args.phase,
        'confirmatory_final_test': False,
        'campaign_sha256': campaign.digest(),
        'allocation_design_sha256': allocation.digest(),
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
        raise SystemExit('candidate block failed; see retained manifest')


if __name__ == '__main__':
    main()
