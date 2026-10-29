"""Validated, machine-readable schedules for the freshness study."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple


EVENT_KINDS = frozenset({'request', 'update'})
TRANSPORT_MODES = frozenset({'redis-pubsub', 'redis-streams'})


@dataclass(frozen=True)
class TraceEvent:
    event_id: str
    at_ms: int
    kind: str
    workload: str
    key: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id or not isinstance(self.event_id, str):
            raise ValueError('event_id must be a non-empty string')
        if not isinstance(self.at_ms, int) or isinstance(self.at_ms, bool) or self.at_ms < 0:
            raise ValueError('at_ms must be a non-negative integer')
        if self.kind not in EVENT_KINDS:
            raise ValueError(f'unsupported event kind: {self.kind!r}')
        if not self.workload or not self.key:
            raise ValueError('workload and key must be non-empty')
        if not isinstance(self.payload, Mapping):
            raise ValueError('payload must be a mapping')

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'TraceEvent':
        return cls(
            event_id=value['event_id'],
            at_ms=value['at_ms'],
            kind=value['kind'],
            workload=value['workload'],
            key=value['key'],
            payload=dict(value.get('payload', {})),
        )


@dataclass(frozen=True)
class FaultDirective:
    update_event_id: str
    delay_ms: int = 0
    drop: bool = False
    duplicate_delays_ms: Tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.update_event_id:
            raise ValueError('update_event_id must be non-empty')
        if not isinstance(self.delay_ms, int) or isinstance(self.delay_ms, bool) or self.delay_ms < 0:
            raise ValueError('delay_ms must be a non-negative integer')
        if not isinstance(self.drop, bool):
            raise ValueError('drop must be boolean')
        for delay in self.duplicate_delays_ms:
            if not isinstance(delay, int) or isinstance(delay, bool) or delay < 0:
                raise ValueError('duplicate delays must be non-negative integers')
        if self.drop and self.duplicate_delays_ms:
            raise ValueError('a dropped notification cannot also have duplicates')

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'FaultDirective':
        return cls(
            update_event_id=value['update_event_id'],
            delay_ms=value.get('delay_ms', 0),
            drop=value.get('drop', False),
            duplicate_delays_ms=tuple(value.get('duplicate_delays_ms', ())),
        )


@dataclass(frozen=True)
class ScheduledNotification:
    notification_id: str
    source_event_id: str
    source_sequence: int
    copy_index: int
    created_at_ms: int
    deliver_at_ms: Optional[int]
    dropped: bool
    workload: str
    key: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class TraceSchedule:
    trace_id: str
    seed: int
    transport_mode: str
    events: Tuple[TraceEvent, ...]
    faults: Tuple[FaultDirective, ...] = ()
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError('unsupported trace schema version')
        if not self.trace_id:
            raise ValueError('trace_id must be non-empty')
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise ValueError('seed must be an integer')
        if self.transport_mode not in TRANSPORT_MODES:
            raise ValueError(f'unsupported transport mode: {self.transport_mode!r}')

        ids = [event.event_id for event in self.events]
        if len(ids) != len(set(ids)):
            raise ValueError('event IDs must be unique')
        if any(current.at_ms < previous.at_ms for previous, current in zip(self.events, self.events[1:])):
            raise ValueError('events must be ordered by non-decreasing at_ms')

        update_ids = {event.event_id for event in self.events if event.kind == 'update'}
        fault_ids = [fault.update_event_id for fault in self.faults]
        if len(fault_ids) != len(set(fault_ids)):
            raise ValueError('at most one fault directive is allowed per update')
        unknown = set(fault_ids) - update_ids
        if unknown:
            raise ValueError(f'fault directives must reference update events: {sorted(unknown)}')
        try:
            json.dumps(self.to_mapping(), allow_nan=False)
        except (TypeError, ValueError) as error:
            raise ValueError(f'schedule must contain finite JSON-compatible values: {error}') from error

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'TraceSchedule':
        return cls(
            trace_id=value['trace_id'],
            seed=value['seed'],
            transport_mode=value['transport_mode'],
            events=tuple(TraceEvent.from_mapping(item) for item in value['events']),
            faults=tuple(FaultDirective.from_mapping(item) for item in value.get('faults', ())),
            schema_version=value.get('schema_version', 1),
        )

    def to_mapping(self) -> Dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'trace_id': self.trace_id,
            'seed': self.seed,
            'transport_mode': self.transport_mode,
            'events': [asdict(event) for event in self.events],
            'faults': [asdict(fault) for fault in self.faults],
        }

    def digest(self) -> str:
        encoded = json.dumps(
            self.to_mapping(), sort_keys=True, separators=(',', ':'), ensure_ascii=False,
            allow_nan=False,
        ).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()

    def trace_digest(self) -> str:
        """Identify the exogenous event trace independently of injected faults."""
        value = {
            'schema_version': self.schema_version,
            'trace_id': self.trace_id,
            'seed': self.seed,
            'events': [asdict(event) for event in self.events],
        }
        encoded = json.dumps(
            value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False,
        ).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()

    def fault_digest(self) -> str:
        """Identify transport mode and fault directives independently of events."""
        value = {
            'schema_version': self.schema_version,
            'transport_mode': self.transport_mode,
            'faults': [asdict(fault) for fault in self.faults],
        }
        encoded = json.dumps(
            value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False,
        ).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()


def load_schedule(path: str) -> TraceSchedule:
    with open(path, encoding='utf-8') as stream:
        return TraceSchedule.from_mapping(json.load(stream))


def dump_schedule(schedule: TraceSchedule, path: str) -> None:
    with open(path, 'x', encoding='utf-8') as stream:
        json.dump(schedule.to_mapping(), stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
