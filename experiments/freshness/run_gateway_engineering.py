"""Write a semantic-only W1 policy replay artifact for engineering review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .cache_gateway import CacheGateway
from .catalog_workload import CatalogWorkload
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('schedule', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()

    schedule = load_schedule(str(args.schedule))
    results = []
    for policy, options in POLICY_OPTIONS.items():
        workload = CatalogWorkload(product_count=4)
        try:
            gateway = CacheGateway(workload, policy, **options)
            results.append(run_trace(schedule, gateway).to_mapping())
        finally:
            workload.close()

    artifact = {
        'artifact_schema_version': 1,
        'measurement_kind': 'semantic-engineering-only',
        'contains_performance_observations': False,
        'protocol_status': 'pre-freeze-v0.3-do-not-use-as-study-data',
        'schedule_path': str(args.schedule),
        'policy_parameters': POLICY_OPTIONS,
        'runs': results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(artifact, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
