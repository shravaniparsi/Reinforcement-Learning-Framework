"""Execute one matched eight-policy training cost-calibration block."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .allocation_design import AllocationDesign
from .schema import dump_schedule
from .trace_generator import TraceDesign, WORKLOAD_IDS, generate_schedule


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--workload', choices=WORKLOAD_IDS, required=True)
    parser.add_argument('--regime', required=True)
    parser.add_argument('--seed', type=int, required=True)
    args = parser.parse_args()

    allocation = AllocationDesign.load(Path(__file__).with_name('allocation_design_v1.json'))
    trace_design = TraceDesign.load(Path(__file__).with_name('trace_design_v1.json'))
    identity = {
        'stage': 'training',
        'workload': args.workload,
        'regime': args.regime,
        'trace_seed': args.seed,
        'transport': 'redis-pubsub',
        'fault_profile': 'no-fault',
    }
    order = allocation.policy_order(identity)
    schedule = generate_schedule(
        trace_design,
        workload_id=args.workload,
        regime=args.regime,
        partition='training',
        seed=args.seed,
        fault_profile='no-fault',
        transport_mode='redis-pubsub',
    )
    args.output.mkdir(parents=True, exist_ok=False)
    schedule_path = args.output / 'schedule.json'
    dump_schedule(schedule, str(schedule_path))
    attempts = []
    for position, policy in enumerate(order):
        artifact = args.output / ('%02d-%s.json' % (position, policy))
        completed = subprocess.run(
            [
                sys.executable, '-m', 'experiments.freshness.run_instrumented_unit',
                str(schedule_path), policy, str(artifact), '--stage', 'training',
            ],
            text=True,
            capture_output=True,
        )
        attempts.append({
            'position': position,
            'policy': policy,
            'returncode': completed.returncode,
            'stdout': completed.stdout,
            'stderr': completed.stderr,
            'artifact': artifact.name,
        })
        if completed.returncode != 0:
            break
    passed = len(attempts) == 8 and all(item['returncode'] == 0 for item in attempts)
    manifest = {
        'artifact_schema_version': 1,
        'measurement_kind': 'training-cost-calibration-block',
        'stage': 'training',
        'confirmatory_final_test': False,
        'allocation_design_sha256': allocation.digest(),
        'block_identity': identity,
        'policy_order': list(order),
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
        raise SystemExit('cost-calibration block failed; see retained manifest')


if __name__ == '__main__':
    main()
