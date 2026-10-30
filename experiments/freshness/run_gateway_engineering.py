"""Write a semantic-only W1 policy replay artifact for engineering review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .cache_gateway import CacheGateway
from .catalog_workload import CatalogWorkload
from .dashboard_workload import DashboardWorkload
from .dependencies import dashboard_query_affects, realworld_feed_affects
from .realworld_workload import RealWorldFeedWorkload
from .schema import load_schedule
from .trace_runner import run_trace


POLICY_OPTIONS = {
    'bypass': {},
    'conditional-validation': {},
    'fixed-ttl': {'ttl_ms': 25},
    'stale-while-revalidate': {'ttl_ms': 25, 'stale_window_ms': 50},
    'always-invalidate': {},
    'always-update': {},
    'write-reactive': {
        'update_cost': 1,
        'invalidate_cost': 1,
        'miss_cost': 4,
        'initial_expected_writes': 1,
    },
    'event-invalidate-with-repair': {'repair_ms': 25},
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _workload_and_options(workload_id: str):
    if workload_id == CatalogWorkload.workload_id:
        return CatalogWorkload(product_count=4), {}
    if workload_id == RealWorldFeedWorkload.workload_id:
        return RealWorldFeedWorkload(article_count=30), {'affects': realworld_feed_affects}
    if workload_id == DashboardWorkload.workload_id:
        return DashboardWorkload(), {'affects': dashboard_query_affects}
    raise ValueError(f'unsupported engineering workload: {workload_id}')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('schedule', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()

    schedule = load_schedule(str(args.schedule))
    workload_ids = {event.workload for event in schedule.events}
    if len(workload_ids) != 1:
        raise ValueError('engineering replay requires exactly one workload per schedule')
    workload_id = next(iter(workload_ids))
    results = []
    for policy, options in POLICY_OPTIONS.items():
        workload, workload_options = _workload_and_options(workload_id)
        try:
            gateway = CacheGateway(workload, policy, **workload_options, **options)
            results.append(run_trace(schedule, gateway).to_mapping())
        finally:
            workload.close()

    artifact = {
        'artifact_schema_version': 1,
        'measurement_kind': 'semantic-engineering-only',
        'contains_performance_observations': False,
        'protocol_status': 'pre-freeze-v0.4-draft-do-not-use-as-study-data',
        'workload_id': workload_id,
        'schedule_path': str(args.schedule),
        'source_sha256': {
            'run_gateway_engineering.py': _sha256(Path(__file__)),
            'cache_gateway.py': _sha256(Path(__file__).with_name('cache_gateway.py')),
            'trace_runner.py': _sha256(Path(__file__).with_name('trace_runner.py')),
            'schedule': _sha256(args.schedule),
        },
        'policy_parameters': POLICY_OPTIONS,
        'runs': results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(artifact, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
