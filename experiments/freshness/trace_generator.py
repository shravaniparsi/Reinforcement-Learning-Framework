"""Prospective bounded synthetic traces for the cache-freshness study."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .schema import FaultDirective, TraceEvent, TraceSchedule, dump_schedule


WORKLOAD_IDS = (
    'mutable-product-v1',
    'svelte-realworld-feed-v1',
    'react-admin-dashboard-v1',
)
PARTITIONS = (
    'engineering', 'training', 'validation', 'variance-planning', 'final-test',
)


@dataclass(frozen=True)
class TraceDesign:
    design_id: str
    updates_per_trace: int
    mean_inter_event_ms: int
    inter_event_jitter_ms: int
    regimes: Mapping[str, Mapping[str, int]]
    partitions: Mapping[str, Mapping[str, int]]
    fault_profiles: Mapping[str, Mapping[str, int]]
    schema_version: int = 1

    @classmethod
    def load(cls, path: Path) -> 'TraceDesign':
        value = json.loads(path.read_text(encoding='utf-8'))
        design = cls(
            design_id=value['design_id'],
            updates_per_trace=value['updates_per_trace'],
            mean_inter_event_ms=value['mean_inter_event_ms'],
            inter_event_jitter_ms=value['inter_event_jitter_ms'],
            regimes=value['regimes'],
            partitions=value['partitions'],
            fault_profiles=value['fault_profiles'],
            schema_version=value.get('schema_version', 1),
        )
        design.validate()
        return design

    def validate(self) -> None:
        if self.schema_version != 1 or not self.design_id:
            raise ValueError('unsupported or unnamed trace design')
        if self.updates_per_trace != 100:
            raise ValueError('trace design v1 requires exactly 100 updates')
        if self.inter_event_jitter_ms < 0 or self.mean_inter_event_ms <= self.inter_event_jitter_ms:
            raise ValueError('invalid inter-event timing bounds')
        if set(self.partitions) != set(PARTITIONS):
            raise ValueError('trace design partitions are incomplete')
        seed_ranges = []
        for partition in PARTITIONS:
            item = self.partitions[partition]
            start, count = item['seed_start'], item['seed_count']
            if not isinstance(start, int) or not isinstance(count, int) or count < 1:
                raise ValueError('partition seed ranges must be positive integer ranges')
            seed_ranges.append(set(range(start, start + count)))
        for index, first in enumerate(seed_ranges):
            if any(first & second for second in seed_ranges[index + 1:]):
                raise ValueError('partition seed ranges must not overlap')
        for name, profile in self.fault_profiles.items():
            if not name:
                raise ValueError('fault profile names must be non-empty')
            if profile['delay_ms'] not in {0, 1, 10, 100}:
                raise ValueError('fault delay is outside the frozen grid')
            for field in ('loss_percent', 'duplicate_percent', 'reorder_percent'):
                if profile[field] not in {0, 1, 5, 10}:
                    raise ValueError(f'{field} is outside the frozen percentage grid')

    def digest(self) -> str:
        value = {
            'schema_version': self.schema_version,
            'design_id': self.design_id,
            'updates_per_trace': self.updates_per_trace,
            'mean_inter_event_ms': self.mean_inter_event_ms,
            'inter_event_jitter_ms': self.inter_event_jitter_ms,
            'regimes': self.regimes,
            'partitions': self.partitions,
            'fault_profiles': self.fault_profiles,
        }
        encoded = json.dumps(
            value, sort_keys=True, separators=(',', ':'), allow_nan=False,
        ).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()


def _derived_seed(*parts: Any) -> int:
    encoded = json.dumps(parts, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return int.from_bytes(hashlib.sha256(encoded).digest()[:8], 'big')


def _event_kinds(requests: int, updates: int, rng: random.Random) -> List[str]:
    if requests < 1 or updates < 1:
        raise ValueError('a trace requires requests and updates')
    remaining = ['request'] * (requests - 1) + ['update'] * updates
    rng.shuffle(remaining)
    return ['request'] + remaining


class _WorkloadEvents:
    def __init__(self, workload_id: str, seed: int) -> None:
        self.workload_id = workload_id
        self.rng = random.Random(_derived_seed('workload-events', workload_id, seed))
        self.global_revision = 0
        self.product_revisions: Dict[str, int] = {}
        self.update_index = 0
        self.request_index = 0

    def request(self, event_id: str, at_ms: int) -> TraceEvent:
        self.request_index += 1
        if self.workload_id == 'mutable-product-v1':
            key = self._mixture_key('product', 4, 20)
            revision = self.product_revisions.get(key, 0)
        elif self.workload_id == 'svelte-realworld-feed-v1':
            queries = (
                '/api/articles?limit=10&offset=0',
                '/api/articles?tag=rendering&limit=10&offset=0',
                '/api/articles?tag=accessibility&limit=10&offset=0',
                '/api/articles?limit=10&offset=10',
            )
            key = self.rng.choice(queries)
            revision = self.global_revision
        elif self.workload_id == 'react-admin-dashboard-v1':
            queries = (
                '/api/orders?sort=["date","DESC"]&range=[0,9]',
                '/api/reviews?filter={"status":"pending"}&sort=["date","DESC"]&range=[0,9]',
                '/api/customers?sort=["id","ASC"]&range=[0,7]',
            )
            key = self.rng.choice(queries)
            revision = self.global_revision
        else:  # pragma: no cover
            raise AssertionError(self.workload_id)
        return TraceEvent(
            event_id, at_ms, 'request', self.workload_id, key,
            {'decision_revision': revision},
        )

    def update(self, event_id: str, at_ms: int) -> TraceEvent:
        self.update_index += 1
        if self.workload_id == 'mutable-product-v1':
            key = self._mixture_key('product', 4, 20)
            revision = self.product_revisions.get(key, 0) + 1
            self.product_revisions[key] = revision
            selector = self.update_index % 3
            if selector == 0:
                changes = {'price_cents': 2000 + self.update_index * 11}
            elif selector == 1:
                changes = {'available': self.update_index % 2 == 0}
            else:
                changes = {'description': f'Prospective trace update {self.update_index}.'}
            mutation = {'key': key, 'changes': changes}
        elif self.workload_id == 'svelte-realworld-feed-v1':
            self.global_revision += 1
            revision = self.global_revision
            article_index = 20 + self.rng.randrange(10)
            key = f'independent-note-{article_index}'
            selector = self.update_index % 3
            if selector == 0:
                changes = {'title': f'Prospective title {self.update_index}'}
            elif selector == 1:
                changes = {'description': f'Prospective description {self.update_index}.'}
            else:
                changes = {'tagList': ['rendering' if self.update_index % 2 else 'accessibility']}
            mutation = {'operation': 'update', 'slug': key, 'changes': changes}
        elif self.workload_id == 'react-admin-dashboard-v1':
            self.global_revision += 1
            revision = self.global_revision
            resource = ('orders', 'reviews', 'customers')[self.update_index % 3]
            if resource == 'orders':
                record_id = 1 + self.rng.randrange(12)
                changes = {'total': 100 + self.update_index * 3}
            elif resource == 'reviews':
                record_id = 1 + self.rng.randrange(6)
                changes = {'comment': f'Prospective review {self.update_index}.'}
            else:
                record_id = 1 + self.rng.randrange(8)
                changes = {'last_name': f'Trace{self.update_index}'}
            key = f'{resource}:{record_id}'
            mutation = {
                'resource': resource, 'operation': 'update', 'id': record_id,
                'changes': changes,
            }
        else:  # pragma: no cover
            raise AssertionError(self.workload_id)
        return TraceEvent(
            event_id, at_ms, 'update', self.workload_id, key,
            {'expected_revision': revision, 'mutation': mutation},
        )

    def _mixture_key(self, prefix: str, hot_count: int, total_count: int) -> str:
        if self.rng.random() < 0.8:
            index = 1 + self.rng.randrange(hot_count)
        else:
            index = hot_count + 1 + self.rng.randrange(total_count - hot_count)
        return f'{prefix}-{index}'


def _base_events(
    design: TraceDesign, workload_id: str, regime: str, seed: int,
) -> Tuple[TraceEvent, ...]:
    requests = design.regimes[regime]['requests_per_trace']
    ordering_rng = random.Random(_derived_seed('event-order', workload_id, regime, seed))
    timing_rng = random.Random(_derived_seed('event-timing', workload_id, regime, seed))
    kinds = _event_kinds(requests, design.updates_per_trace, ordering_rng)
    builder = _WorkloadEvents(workload_id, seed)
    events = []
    at_ms = 0
    request_number = 0
    update_number = 0
    for kind in kinds:
        if events:
            at_ms += timing_rng.randint(
                design.mean_inter_event_ms - design.inter_event_jitter_ms,
                design.mean_inter_event_ms + design.inter_event_jitter_ms,
            )
        if kind == 'request':
            request_number += 1
            events.append(builder.request(f'r{request_number:04d}', at_ms))
        else:
            update_number += 1
            events.append(builder.update(f'u{update_number:04d}', at_ms))
    return tuple(events)


def _exact_count(percent: int, total: int) -> int:
    product = percent * total
    if product % 100:
        raise ValueError('fault percentage does not yield an exact event count')
    return product // 100


def _faults(
    design: TraceDesign,
    profile_name: str,
    events: Sequence[TraceEvent],
    seed: int,
) -> Tuple[FaultDirective, ...]:
    profile = design.fault_profiles[profile_name]
    updates = [event for event in events if event.kind == 'update']
    rng = random.Random(_derived_seed('faults', profile_name, seed))
    indices = list(range(len(updates)))
    rng.shuffle(indices)

    loss_count = _exact_count(profile['loss_percent'], len(updates))
    duplicate_count = _exact_count(profile['duplicate_percent'], len(updates))
    reorder_count = _exact_count(profile['reorder_percent'], len(updates))
    lost = set(indices[:loss_count])
    cursor = loss_count
    duplicated = set(indices[cursor:cursor + duplicate_count])

    available_pairs = [
        index for index in range(len(updates) - 1)
        if index not in lost and index + 1 not in lost
    ]
    rng.shuffle(available_pairs)
    reordered = []
    occupied = set()
    for index in available_pairs:
        if len(reordered) == reorder_count:
            break
        if index in occupied or index + 1 in occupied:
            continue
        reordered.append(index)
        occupied.update((index, index + 1))
    if len(reordered) != reorder_count:
        raise ValueError('could not select the declared number of non-overlapping reorder pairs')

    delay_by_index = {index: profile['delay_ms'] for index in range(len(updates))}
    for index in reordered:
        gap = updates[index + 1].at_ms - updates[index].at_ms
        delay_by_index[index] = max(delay_by_index[index], gap + profile['delay_ms'] + 1)

    directives = []
    for index, event in enumerate(updates):
        drop = index in lost
        delay = delay_by_index[index]
        duplicate_delays = ()
        if index in duplicated and not drop:
            duplicate_delays = (delay + 1,)
        if drop or delay or duplicate_delays:
            directives.append(FaultDirective(
                update_event_id=event.event_id,
                delay_ms=delay,
                drop=drop,
                duplicate_delays_ms=duplicate_delays,
            ))
    return tuple(directives)


def generate_schedule(
    design: TraceDesign,
    *,
    workload_id: str,
    regime: str,
    partition: str,
    seed: int,
    fault_profile: str,
    transport_mode: str,
) -> TraceSchedule:
    if workload_id not in WORKLOAD_IDS:
        raise ValueError(f'unsupported workload: {workload_id}')
    if regime not in design.regimes:
        raise ValueError(f'unsupported regime: {regime}')
    if partition not in design.partitions:
        raise ValueError(f'unsupported partition: {partition}')
    partition_range = design.partitions[partition]
    allowed = range(
        partition_range['seed_start'],
        partition_range['seed_start'] + partition_range['seed_count'],
    )
    if seed not in allowed:
        raise ValueError(f'seed {seed} is outside the {partition} partition')
    if fault_profile not in design.fault_profiles:
        raise ValueError(f'unsupported fault profile: {fault_profile}')
    events = _base_events(design, workload_id, regime, seed)
    faults = _faults(design, fault_profile, events, seed)
    return TraceSchedule(
        trace_id=(
            f'{design.design_id}:{partition}:{workload_id}:{regime}:'
            f's{seed}'
        ),
        seed=seed,
        transport_mode=transport_mode,
        events=events,
        faults=faults,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument(
        '--design', type=Path, default=Path(__file__).with_name('trace_design_v1.json'),
    )
    parser.add_argument('--workload', choices=WORKLOAD_IDS, required=True)
    parser.add_argument('--regime', required=True)
    parser.add_argument('--partition', choices=PARTITIONS, required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--fault-profile', required=True)
    parser.add_argument(
        '--transport', choices=('redis-pubsub', 'redis-streams'), required=True,
    )
    args = parser.parse_args()
    design = TraceDesign.load(args.design)
    schedule = generate_schedule(
        design,
        workload_id=args.workload,
        regime=args.regime,
        partition=args.partition,
        seed=args.seed,
        fault_profile=args.fault_profile,
        transport_mode=args.transport,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    dump_schedule(schedule, str(args.output))


if __name__ == '__main__':
    main()
