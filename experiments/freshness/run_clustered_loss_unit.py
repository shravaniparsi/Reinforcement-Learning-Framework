"""Run one instrumented unit belonging only to the clustered-loss extension."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from pathlib import Path

from .cache_gateway import CacheGateway
from .clustered_loss_measurement import summarize_clustered_loss
from .measurement import summarize_trace_run
from .redis_delivery import RedisNotificationTransport
from .run_gateway_engineering import POLICY_OPTIONS, _workload_and_options
from .schema import load_schedule
from .trace_runner import run_trace


STAGES = ('extension-engineering', 'extension-precision-planning')
POLICIES = (
    'conditional-validation', 'fixed-ttl', 'always-invalidate',
    'event-invalidate-with-repair',
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('schedule', type=Path)
    parser.add_argument('policy', choices=POLICIES)
    parser.add_argument('output', type=Path)
    parser.add_argument('--stage', choices=STAGES, required=True)
    parser.add_argument('--redis-server', default='redis-server')
    parser.add_argument('--options-file', type=Path)
    parser.add_argument('--compact', action='store_true')
    args = parser.parse_args()

    schedule = load_schedule(str(args.schedule))
    expected_prefix = f'freshness-clustered-loss-extension-v1:{args.stage}:'
    if not schedule.trace_id.startswith(expected_prefix):
        raise ValueError('schedule partition does not match the extension stage')
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
        gateway = CacheGateway(workload, args.policy, **workload_options, **options)
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
    summary = dict(summarize_trace_run(run))
    summary.update(summarize_clustered_loss(run, schedule))
    artifact = {
        'artifact_schema_version': 1,
        'measurement_kind': 'clustered-loss-extension-trace-unit',
        'stage': args.stage,
        'confirmatory_final_test': False,
        'final_extension_collection': False,
        'protocol': 'clustered-loss-protocol-v0.1',
        'workload_id': workload_id,
        'policy_parameters': options,
        'compact_raw_observations': args.compact,
        'host_manifest': {
            'pid': os.getpid(), 'platform': platform.platform(), 'python': sys.version,
        },
        'source_sha256': {
            'schedule': _sha256(args.schedule),
            'run_clustered_loss_unit.py': _sha256(Path(__file__)),
            'clustered_loss_measurement.py': _sha256(
                Path(__file__).with_name('clustered_loss_measurement.py')
            ),
            'measurement.py': _sha256(Path(__file__).with_name('measurement.py')),
            'redis_delivery.py': _sha256(Path(__file__).with_name('redis_delivery.py')),
            'cache_gateway.py': _sha256(Path(__file__).with_name('cache_gateway.py')),
            'trace_runner.py': _sha256(Path(__file__).with_name('trace_runner.py')),
        },
        'summary': summary,
        'run': run_mapping,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(artifact, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
