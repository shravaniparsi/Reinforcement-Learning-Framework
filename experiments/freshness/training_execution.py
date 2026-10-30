"""Bind frozen training candidates to locked workload/regime byte costs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Tuple

from .training_campaign import TrainingCampaign


@dataclass(frozen=True)
class TrainingUnitSpec:
    unit_id: str
    policy: str
    options: Mapping[str, Any]
    candidate: bool
    declared_order: int


def load_locked_costs(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    if (
        value.get('measurement_kind') != 'training-serialized-byte-cost-lock'
        or value.get('stage') != 'training'
        or value.get('confirmatory_final_test') is not False
    ):
        raise ValueError('invalid or non-training byte-cost lock')
    return value


def _cost_options(cost_lock: Mapping[str, Any], workload: str, regime: str) -> dict:
    try:
        costs = cost_lock['costs'][workload][regime]
    except KeyError as error:
        raise ValueError('byte-cost lock lacks the requested workload/regime') from error
    return {
        'update_cost': costs['update_cost_bytes'],
        'invalidate_cost': costs['invalidate_cost_bytes'],
        'miss_cost': costs['miss_cost_bytes'],
    }


def unit_specs(
    campaign: TrainingCampaign,
    cost_lock: Mapping[str, Any],
    phase: str,
    workload: str,
    regime: str,
) -> Tuple[TrainingUnitSpec, ...]:
    cost_options = _cost_options(cost_lock, workload, regime)
    specs = []
    if phase == 'time-candidates':
        for policy in ('fixed-ttl', 'stale-while-revalidate'):
            for candidate in campaign.candidates(policy):
                specs.append(TrainingUnitSpec(
                    candidate.candidate_id, policy, dict(candidate.options), True,
                    candidate.declared_order,
                ))
        controls = (
            ('control:bypass', 'bypass', {}),
            ('control:conditional-validation', 'conditional-validation', {}),
            ('control:always-invalidate', 'always-invalidate', {}),
            ('control:always-update', 'always-update', {}),
            ('control:write-reactive', 'write-reactive', {
                **cost_options, 'initial_expected_writes': 1.0,
            }),
            ('control:event-invalidate-with-repair', 'event-invalidate-with-repair', {
                'repair_ms': 25,
            }),
        )
    elif phase == 'event-candidates':
        for candidate in campaign.candidates('event-invalidate-with-repair'):
            specs.append(TrainingUnitSpec(
                candidate.candidate_id, candidate.policy, dict(candidate.options), True,
                candidate.declared_order,
            ))
        for candidate in campaign.candidates('write-reactive'):
            specs.append(TrainingUnitSpec(
                candidate.candidate_id,
                candidate.policy,
                {**cost_options, **dict(candidate.options)},
                True,
                candidate.declared_order,
            ))
        controls = (
            ('control:bypass', 'bypass', {}),
            ('control:conditional-validation', 'conditional-validation', {}),
            ('control:fixed-ttl', 'fixed-ttl', {'ttl_ms': 25}),
            ('control:stale-while-revalidate', 'stale-while-revalidate', {
                'ttl_ms': 25, 'stale_window_ms': 50,
            }),
            ('control:always-invalidate', 'always-invalidate', {}),
            ('control:always-update', 'always-update', {}),
        )
    else:
        raise ValueError('unsupported training candidate phase')
    start = len(specs)
    specs.extend(
        TrainingUnitSpec(unit_id, policy, options, False, start + index)
        for index, (unit_id, policy, options) in enumerate(controls)
    )
    if len({item.unit_id for item in specs}) != len(specs):
        raise ValueError('training unit IDs must be unique')
    return tuple(specs)
