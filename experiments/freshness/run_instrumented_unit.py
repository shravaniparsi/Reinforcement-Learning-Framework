"""Run one source-bound instrumented freshness unit through real Redis."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from pathlib import Path

from .cache_gateway import CacheGateway
from .measurement import summarize_trace_run
from .redis_delivery import RedisNotificationTransport
from .run_gateway_engineering import POLICY_OPTIONS, _workload_and_options
from .schema import load_schedule
from .trace_runner import run_trace


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('schedule', type=Path)
    parser.add_argument('policy', choices=tuple(POLICY_OPTIONS))
    parser.add_argument('output', type=Path)
    parser.add_argument(
        '--stage',
        choices=('engineering', 'training', 'validation', 'variance-planning', 'final-test'),
        required=True,
    )
    parser.add_argument('--confirmatory-final-test', action='store_true')
    parser.add_argument('--redis-server', default='redis-server')
    parser.add_argument('--options-file', type=Path)
    parser.add_argument('--compact', action='store_true')
    args = parser.parse_args()

    schedule = load_schedule(str(args.schedule))
    is_final = args.stage == 'final-test'
    if is_final != args.confirmatory_final_test:
        raise ValueError('final-test stage and explicit confirmatory authorization must agree')
    design_id = 'freshness-bounded-synthetic-v2' if is_final else 'freshness-bounded-synthetic-v1'
    expected_prefix = '%s:%s:' % (design_id, args.stage)
    if not schedule.trace_id.startswith(expected_prefix):
        raise ValueError('schedule partition does not match the declared collection stage')
    workload_ids = {event.workload for event in schedule.events}
    if len(workload_ids) != 1:
        raise ValueError('an instrumented unit requires exactly one workload')
    workload_id = next(iter(workload_ids))
    options = POLICY_OPTIONS[args.policy]
    if args.options_file is not None:
        options = json.loads(args.options_file.read_text(encoding='utf-8'))
        if not isinstance(options, dict):
            raise ValueError('policy options file must contain a JSON object')
    workload, workload_options = _workload_and_options(workload_id)
    try:
        gateway = CacheGateway(
            workload, args.policy, **workload_options, **options,
        )
        with RedisNotificationTransport(
            schedule.transport_mode, redis_server=args.redis_server,
        ) as transport:
            run = run_trace(schedule, gateway, transport=transport)
    finally:
        workload.close()

    run_mapping = run.to_mapping(include_measurements=True)
    if args.compact:
        for observation in run_mapping['observations']:
            observation.pop('content', None)
    artifact = {
        'artifact_schema_version': 1,
        'measurement_kind': 'instrumented-freshness-trace-unit',
        'stage': args.stage,
        'confirmatory_final_test': is_final,
        'protocol': 'freshness-protocol-v0.5' if is_final else 'freshness-protocol-v0.4',
        'workload_id': workload_id,
        'policy_parameters': options,
        'compact_raw_observations': args.compact,
        'host_manifest': {
            'pid': os.getpid(),
            'platform': platform.platform(),
            'python': sys.version,
        },
        'source_sha256': {
            'schedule': _sha256(args.schedule),
            'run_instrumented_unit.py': _sha256(Path(__file__)),
            'measurement.py': _sha256(Path(__file__).with_name('measurement.py')),
            'redis_delivery.py': _sha256(Path(__file__).with_name('redis_delivery.py')),
            'cache_gateway.py': _sha256(Path(__file__).with_name('cache_gateway.py')),
            'trace_runner.py': _sha256(Path(__file__).with_name('trace_runner.py')),
        },
        'summary': summarize_trace_run(run),
        'run': run_mapping,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(artifact, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
