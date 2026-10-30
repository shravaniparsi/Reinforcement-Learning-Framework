"""Bind all policy families to the immutable training locks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Tuple

from .training_execution import load_locked_costs, load_time_lock


@dataclass(frozen=True)
class LockedUnitSpec:
    unit_id: str
    policy: str
    options: Mapping[str, Any]


def load_event_lock(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    if (
        value.get('measurement_kind') != 'training-event-parameter-lock'
        or value.get('stage') != 'training'
        or value.get('confirmatory_final_test') is not False
    ):
        raise ValueError('invalid or non-training event-parameter lock')
    return value


def locked_unit_specs(
    cost_lock: Mapping[str, Any],
    time_lock: Mapping[str, Any],
    event_lock: Mapping[str, Any],
    workload: str,
    regime: str,
) -> Tuple[LockedUnitSpec, ...]:
    try:
        costs = cost_lock['costs'][workload][regime]
        time_options = time_lock['selected'][workload][regime]
        event_options = event_lock['selected'][workload][regime]
        fixed = dict(time_options['fixed-ttl']['options'])
        swr = dict(time_options['stale-while-revalidate']['options'])
        reactive = dict(event_options['write-reactive']['options'])
        repair = dict(event_options['event-invalidate-with-repair']['options'])
    except KeyError as error:
        raise ValueError('a training lock lacks the requested workload/regime') from error
    expected_costs = {
        'update_cost': costs['update_cost_bytes'],
        'invalidate_cost': costs['invalidate_cost_bytes'],
        'miss_cost': costs['miss_cost_bytes'],
    }
    if any(reactive.get(key) != value for key, value in expected_costs.items()):
        raise ValueError('write-reactive options differ from the serialized-byte cost lock')
    specifications = (
        LockedUnitSpec('locked:bypass', 'bypass', {}),
        LockedUnitSpec('locked:conditional-validation', 'conditional-validation', {}),
        LockedUnitSpec('locked:fixed-ttl', 'fixed-ttl', fixed),
        LockedUnitSpec('locked:stale-while-revalidate', 'stale-while-revalidate', swr),
        LockedUnitSpec('locked:always-invalidate', 'always-invalidate', {}),
        LockedUnitSpec('locked:always-update', 'always-update', {}),
        LockedUnitSpec('locked:write-reactive', 'write-reactive', reactive),
        LockedUnitSpec(
            'locked:event-invalidate-with-repair', 'event-invalidate-with-repair', repair,
        ),
    )
    if len({item.unit_id for item in specifications}) != len(specifications):
        raise ValueError('locked unit IDs must be unique')
    return specifications


__all__ = [
    'LockedUnitSpec', 'load_event_lock', 'load_locked_costs', 'load_time_lock',
    'locked_unit_specs',
]
