"""Deterministic logical-time executor for gateway engineering traces."""

from __future__ import annotations

import heapq
import copy
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Tuple

from .cache_gateway import CacheGateway, GatewayObservation
from .fault_schedule import materialize_notifications
from .schema import ScheduledNotification, TraceSchedule


@dataclass(frozen=True)
class TraceRun:
    trace_id: str
    policy: str
    schedule_sha256: str
    trace_sha256: str
    fault_sha256: str
    observations: Tuple[GatewayObservation, ...]
    committed_event_ids: Tuple[str, ...]
    delivered_notification_ids: Tuple[str, ...]
    duplicate_notification_ids: Tuple[str, ...]
    dropped_notification_ids: Tuple[str, ...]
    publication_records: Tuple[Mapping[str, Any], ...]
    final_gateway_state: Mapping[str, Any]

    def to_mapping(self) -> Mapping[str, Any]:
        return {
            **asdict(self),
            'observations': [asdict(item) for item in self.observations],
        }


def _request_revision(payload: Mapping[str, Any]) -> int:
    revision = payload.get('decision_revision')
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        raise ValueError('request events require a non-negative decision_revision')
    return revision


def _mutation(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    mutation = payload.get('mutation')
    if not isinstance(mutation, Mapping):
        raise ValueError('update events require a mutation mapping')
    return mutation


def _encoded_size(value: Any) -> int:
    return len(json.dumps(
        value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False,
    ).encode('utf-8'))


def _prepare_publication(
    gateway: CacheGateway,
    event_id: str,
    notification_key: str,
    payload: Mapping[str, Any],
    revision: int,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    prepared = dict(gateway.prepare_notification(event_id, notification_key, payload))
    actions = prepared.get('_cache_actions', {})
    query_updates: Dict[str, Mapping[str, Any]] = {}
    origin_reads = 0
    origin_body_bytes = 0
    for cache_key, action in actions.items():
        if action != 'update':
            continue
        if cache_key == notification_key and prepared.get('content') is not None:
            continue
        record = gateway.workload.read(cache_key)
        if record.decision_revision != revision:
            raise ValueError(
                f'publication snapshot revision {record.decision_revision} differs from '
                f'commit revision {revision} for {cache_key}'
            )
        query_updates[cache_key] = {
            'revision': revision,
            'content': copy.deepcopy(record.content),
            'content_sha256': record.content_sha256,
        }
        origin_reads += 1
        origin_body_bytes += record.response_body_bytes
    if query_updates:
        prepared['query_updates'] = query_updates
    record = {
        'event_id': event_id,
        'revision': revision,
        'actions': dict(actions),
        'query_update_count': len(query_updates),
        'publisher_origin_reads': origin_reads,
        'publisher_origin_response_body_bytes': origin_body_bytes,
        'notification_body_bytes': _encoded_size({
            'key': notification_key, 'payload': prepared,
        }),
    }
    return prepared, record


def run_trace(schedule: TraceSchedule, gateway: CacheGateway) -> TraceRun:
    """Replay one schedule without allowing policy work to move exogenous events."""

    workload_id = gateway.workload.workload_id
    mismatched = [event.event_id for event in schedule.events if event.workload != workload_id]
    if mismatched:
        raise ValueError(f'schedule workload mismatch for events: {mismatched}')

    delivered_templates, dropped = materialize_notifications(schedule)
    templates_by_source: Dict[str, List[ScheduledNotification]] = {}
    for item in delivered_templates:
        templates_by_source.setdefault(item.source_event_id, []).append(item)

    gateway.reset(schedule.seed)
    pending: List[tuple] = []
    committed: List[str] = []
    delivered_ids: List[str] = []
    duplicate_ids: List[str] = []
    observations: List[GatewayObservation] = []
    publication_records: List[Mapping[str, Any]] = []
    commit_payloads: Dict[str, Mapping[str, Any]] = {}

    def deliver_through(at_ms: int) -> None:
        while pending and pending[0][0] <= at_ms:
            _, source_sequence, copy_index, template = heapq.heappop(pending)
            accepted = gateway.notify(
                template.source_event_id,
                template.key,
                commit_payloads[template.source_event_id],
                at_ms=template.deliver_at_ms,
            )
            if accepted:
                delivered_ids.append(template.notification_id)
            else:
                duplicate_ids.append(template.notification_id)

    for event in schedule.events:
        deliver_through(event.at_ms)
        if event.kind == 'update':
            commit = gateway.workload.commit(_mutation(event.payload), at_ms=event.at_ms)
            expected_revision = event.payload.get('expected_revision')
            if expected_revision is not None and commit.revision != expected_revision:
                raise ValueError(
                    f'commit revision {commit.revision} differs from expected revision '
                    f'{expected_revision} for {event.event_id}'
                )
            prepared, publication_record = _prepare_publication(
                gateway,
                event.event_id,
                event.key,
                commit.notification_payload,
                commit.revision,
            )
            commit_payloads[event.event_id] = prepared
            publication_records.append(publication_record)
            committed.append(event.event_id)
            for template in templates_by_source.get(event.event_id, ()):
                heapq.heappush(
                    pending,
                    (
                        template.deliver_at_ms,
                        template.source_sequence,
                        template.copy_index,
                        template,
                    ),
                )
            deliver_through(event.at_ms)
        else:
            observations.append(gateway.read(
                event.key,
                at_ms=event.at_ms,
                decision_revision=_request_revision(event.payload),
            ))

    deliver_through(2**63 - 1)
    return TraceRun(
        trace_id=schedule.trace_id,
        policy=gateway.policy,
        schedule_sha256=schedule.digest(),
        trace_sha256=schedule.trace_digest(),
        fault_sha256=schedule.fault_digest(),
        observations=tuple(observations),
        committed_event_ids=tuple(committed),
        delivered_notification_ids=tuple(delivered_ids),
        duplicate_notification_ids=tuple(duplicate_ids),
        dropped_notification_ids=tuple(item.notification_id for item in dropped),
        publication_records=tuple(publication_records),
        final_gateway_state=gateway.state(),
    )
