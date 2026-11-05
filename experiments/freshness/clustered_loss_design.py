"""Prospective matched-count clustered-loss extension design."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence, Tuple

from .schema import FaultDirective, TraceSchedule
from .trace_generator import TraceDesign, WORKLOAD_IDS, _base_events, _derived_seed


EXTENSION_PARTITIONS = ('extension-engineering', 'extension-precision-planning')
FAULT_PROFILES = (
    'no-fault', 'dispersed-10', 'single-burst-10', 'repeated-bursts-10',
)


@dataclass(frozen=True)
class ClusteredLossDesign:
    source: Mapping[str, Any]

    @classmethod
    def load(cls, path: Path, base: TraceDesign) -> 'ClusteredLossDesign':
        design = cls(json.loads(path.read_text(encoding='utf-8')))
        design.validate(base)
        return design

    def validate(self, base: TraceDesign) -> None:
        value = self.source
        if value.get('schema_version') != 1 or not value.get('design_id'):
            raise ValueError('unsupported or unnamed clustered-loss design')
        if value.get('protocol') != 'clustered-loss-protocol-v0.1':
            raise ValueError('unexpected clustered-loss protocol')
        if value.get('base_trace_design') != base.design_id:
            raise ValueError('clustered-loss design names a different base trace design')
        if value.get('updates_per_trace') != base.updates_per_trace:
            raise ValueError('clustered-loss and base update counts differ')
        if tuple(value.get('fault_profiles', ())) != FAULT_PROFILES:
            raise ValueError('clustered-loss fault profiles differ from the protocol')
        if set(value.get('partitions', {})) != set(EXTENSION_PARTITIONS):
            raise ValueError('clustered-loss partitions are incomplete')
        ranges = []
        for name in EXTENSION_PARTITIONS:
            item = value['partitions'][name]
            start, count = item.get('seed_start'), item.get('seed_count')
            if not isinstance(start, int) or not isinstance(count, int) or count < 1:
                raise ValueError('extension seed ranges must be positive integer ranges')
            current = set(range(start, start + count))
            if any(current & previous for previous in ranges):
                raise ValueError('extension seed ranges must not overlap')
            ranges.append(current)
        base_seeds = set()
        for item in base.partitions.values():
            base_seeds.update(range(item['seed_start'], item['seed_start'] + item['seed_count']))
        if any(base_seeds & current for current in ranges):
            raise ValueError('extension seeds overlap the original study')
        prefix = value.get('protected_prefix_updates')
        suffix = value.get('protected_suffix_updates')
        loss = value.get('loss_count')
        if (prefix, suffix, loss) != (20, 20, 10):
            raise ValueError('clustered-loss fault budget or recovery guards changed')
        if prefix + suffix + loss > base.updates_per_trace:
            raise ValueError('clustered-loss protected windows leave too few updates')
        if set(value.get('workloads', ())) != set(WORKLOAD_IDS):
            raise ValueError('extension workloads are incomplete')
        if set(value.get('regimes', ())) != set(base.regimes):
            raise ValueError('extension regimes are incomplete')
        if set(value.get('transports', ())) != {'redis-pubsub', 'redis-streams'}:
            raise ValueError('extension transports are incomplete')
        if set(value.get('policies', ())) != {
            'conditional-validation', 'fixed-ttl', 'always-invalidate',
            'event-invalidate-with-repair',
        }:
            raise ValueError('extension policy set changed')
        if value.get('final_collection_authorized') is not False:
            raise ValueError('a precision-planning design cannot authorize final collection')

    def digest(self) -> str:
        encoded = json.dumps(
            self.source, sort_keys=True, separators=(',', ':'), allow_nan=False,
        ).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()

    def contains(self, identity: Mapping[str, Any]) -> bool:
        partition = identity.get('stage')
        if partition not in EXTENSION_PARTITIONS:
            return False
        item = self.source['partitions'][partition]
        seed = identity.get('trace_seed')
        return (
            identity.get('workload') in self.source['workloads']
            and identity.get('regime') in self.source['regimes']
            and identity.get('fault_profile') in self.source['fault_profiles']
            and identity.get('transport') in self.source['transports']
            and isinstance(seed, int) and not isinstance(seed, bool)
            and item['seed_start'] <= seed < item['seed_start'] + item['seed_count']
        )


def _sample_dispersed(eligible: Sequence[int], count: int, rng: random.Random) -> Tuple[int, ...]:
    """Sample non-adjacent indices so one loss episode is not mislabeled dispersed."""
    for _ in range(10_000):
        chosen = tuple(sorted(rng.sample(tuple(eligible), count)))
        if all(right - left > 1 for left, right in zip(chosen, chosen[1:])):
            return chosen
    raise RuntimeError('could not construct a non-adjacent dispersed schedule')


def _sample_two_bursts(eligible: Sequence[int], rng: random.Random) -> Tuple[int, ...]:
    minimum, maximum = min(eligible), max(eligible)
    candidates = [
        (first, second)
        for first in range(minimum, maximum - 3)
        for second in range(first + 10, maximum - 3)
        if first + 4 <= maximum and second + 4 <= maximum
    ]
    first, second = rng.choice(candidates)
    return tuple(range(first, first + 5)) + tuple(range(second, second + 5))


def loss_indices(design: ClusteredLossDesign, profile: str, seed: int) -> Tuple[int, ...]:
    if profile not in FAULT_PROFILES:
        raise ValueError(f'unsupported clustered-loss profile: {profile}')
    if profile == 'no-fault':
        return ()
    value = design.source
    first = value['protected_prefix_updates']
    stop = value['updates_per_trace'] - value['protected_suffix_updates']
    eligible = tuple(range(first, stop))
    count = value['loss_count']
    rng = random.Random(_derived_seed('clustered-loss-v1', profile, seed))
    if profile == 'dispersed-10':
        return _sample_dispersed(eligible, count, rng)
    if profile == 'single-burst-10':
        start = rng.choice(tuple(range(first, stop - count + 1)))
        return tuple(range(start, start + count))
    if profile == 'repeated-bursts-10':
        return _sample_two_bursts(eligible, rng)
    raise AssertionError(profile)


def generate_clustered_schedule(
    design: ClusteredLossDesign,
    base: TraceDesign,
    *,
    workload_id: str,
    regime: str,
    partition: str,
    seed: int,
    fault_profile: str,
    transport_mode: str,
) -> TraceSchedule:
    identity = {
        'stage': partition, 'workload': workload_id, 'regime': regime,
        'trace_seed': seed, 'fault_profile': fault_profile, 'transport': transport_mode,
    }
    if not design.contains(identity):
        raise ValueError('block identity is outside the clustered-loss extension design')
    events = _base_events(base, workload_id, regime, seed)
    updates = [event for event in events if event.kind == 'update']
    indices = loss_indices(design, fault_profile, seed)
    faults = tuple(FaultDirective(updates[index].event_id, drop=True) for index in indices)
    return TraceSchedule(
        trace_id=(
            f"{design.source['design_id']}:{partition}:{workload_id}:{regime}:s{seed}"
        ),
        seed=seed,
        transport_mode=transport_mode,
        events=events,
        faults=faults,
    )


__all__ = [
    'ClusteredLossDesign', 'EXTENSION_PARTITIONS', 'FAULT_PROFILES',
    'generate_clustered_schedule', 'loss_indices',
]
