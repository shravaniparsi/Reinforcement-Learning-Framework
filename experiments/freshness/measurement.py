"""Trace-level outcome summaries for instrumented freshness units."""

from __future__ import annotations

import math
from typing import Any, Mapping

from .trace_runner import TraceRun


def _nearest_rank(values, probability: float) -> int:
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, math.ceil(probability * len(ordered)) - 1))]


def summarize_trace_run(run: TraceRun) -> Mapping[str, Any]:
    observations = run.observations
    if not observations:
        raise ValueError('trace summary requires request observations')
    requests = [item for item in run.operation_measurements if item.operation == 'request']
    if len(requests) != len(observations):
        raise ValueError('request measurements do not match observations')
    latencies = [item.wall_ns for item in requests]
    origin_operations = {}
    for item in observations:
        origin_operations[item.origin_operation] = origin_operations.get(item.origin_operation, 0) + 1
    return {
        'trace_id': run.trace_id,
        'policy': run.policy,
        'schedule_sha256': run.schedule_sha256,
        'trace_sha256': run.trace_sha256,
        'fault_sha256': run.fault_sha256,
        'request_count': len(observations),
        'freshness_violation_count': sum(not item.semantically_fresh for item in observations),
        'freshness_violation_proportion': sum(
            not item.semantically_fresh for item in observations
        ) / len(observations),
        'mean_revision_lag': sum(item.revision_lag for item in observations) / len(observations),
        'max_revision_lag': max(item.revision_lag for item in observations),
        'cache_hit_count': sum(item.cache_hit for item in observations),
        'origin_operations': dict(sorted(origin_operations.items())),
        'origin_response_body_bytes': sum(
            item.origin_response_body_bytes for item in observations
        ),
        'publisher_origin_response_body_bytes': sum(
            item['publisher_origin_response_body_bytes'] for item in run.publication_records
        ),
        'notification_body_bytes': sum(
            item['notification_body_bytes'] for item in run.publication_records
        ),
        'redis_delivery_payload_bytes': sum(
            item['payload_bytes'] for item in run.transport_deliveries
        ),
        'request_wall_ns': {
            'mean': sum(latencies) / len(latencies),
            'p50': _nearest_rank(latencies, 0.50),
            'p95': _nearest_rank(latencies, 0.95),
            'p99': _nearest_rank(latencies, 0.99),
            'max': max(latencies),
        },
        'operation_thread_cpu_ns': sum(
            item.thread_cpu_ns for item in run.operation_measurements
        ),
        'redis_delivery_wall_ns': sum(
            item['wall_ns'] for item in run.transport_deliveries
        ),
        'redis_delivery_thread_cpu_ns': sum(
            item['thread_cpu_ns'] for item in run.transport_deliveries
        ),
    }
