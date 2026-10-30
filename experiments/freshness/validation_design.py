"""Frozen held-out validation campaign contract."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Tuple

from .allocation_design import AllocationDesign
from .trace_generator import TraceDesign, WORKLOAD_IDS


@dataclass(frozen=True)
class ValidationDesign:
    source: Mapping
    campaign_id: str
    partition: str
    workloads: Tuple[str, ...]
    regimes: Tuple[str, ...]
    seed_start: int
    seed_count: int
    fault_profiles: Tuple[str, ...]
    transports: Tuple[str, ...]
    policies: Tuple[str, ...]
    expected_blocks: int
    expected_full_trace_units: int

    @classmethod
    def load(
        cls,
        path: Path,
        trace_design: TraceDesign,
        allocation: AllocationDesign,
    ) -> 'ValidationDesign':
        value = json.loads(path.read_text(encoding='utf-8'))
        design = cls(
            source=value,
            campaign_id=value['campaign_id'],
            partition=value['partition'],
            workloads=tuple(value['workloads']),
            regimes=tuple(value['regimes']),
            seed_start=value['seed_start'],
            seed_count=value['seed_count'],
            fault_profiles=tuple(value['fault_profiles']),
            transports=tuple(value['transports']),
            policies=tuple(value['policies']),
            expected_blocks=value['expected_blocks'],
            expected_full_trace_units=value['expected_full_trace_units'],
        )
        design.validate(trace_design, allocation)
        return design

    def validate(self, trace_design: TraceDesign, allocation: AllocationDesign) -> None:
        if self.source.get('schema_version') != 1 or not self.campaign_id:
            raise ValueError('unsupported or unnamed validation design')
        if self.partition != 'validation' or self.source.get('final_test_authorized') is not False:
            raise ValueError('validation design has an invalid evidence partition')
        partition = trace_design.partitions['validation']
        if (
            self.seed_start != partition['seed_start']
            or self.seed_count != partition['seed_count']
        ):
            raise ValueError('validation seeds differ from the frozen trace partition')
        if set(self.workloads) != set(WORKLOAD_IDS):
            raise ValueError('validation workloads are incomplete')
        if set(self.regimes) != set(trace_design.regimes):
            raise ValueError('validation regimes are incomplete')
        if set(self.fault_profiles) != set(trace_design.fault_profiles):
            raise ValueError('validation fault profiles are incomplete')
        if set(self.transports) != {'redis-pubsub', 'redis-streams'}:
            raise ValueError('validation transports are incomplete')
        if set(self.policies) != set(allocation.policies_per_allocation):
            raise ValueError('validation policies differ from the allocation contract')
        block_count = (
            len(self.workloads) * len(self.regimes) * len(self.fault_profiles)
            * len(self.transports) * self.seed_count
        )
        if self.expected_blocks != block_count:
            raise ValueError('validation block count is inconsistent')
        if self.expected_full_trace_units != block_count * len(self.policies):
            raise ValueError('validation trace-unit count is inconsistent')
        rule = self.source.get('confirmation_rule', {})
        if (
            rule.get('maximum_increase_over_training') != 0.01
            or rule.get('require_all_planned_blocks') is not True
            or rule.get('require_exact_locked_options') is not True
            or rule.get('allow_refitting') is not False
        ):
            raise ValueError('validation confirmation rule differs from the frozen rule')
        time_condition = self.source.get('time_policy_confirmation_condition', {})
        if time_condition != {
            'fault_profiles': ['no-fault'], 'transports': ['redis-pubsub'],
        }:
            raise ValueError('time-policy confirmation condition is invalid')
        event_condition = self.source.get('event_policy_confirmation_condition', {})
        if (
            set(event_condition.get('fault_profiles', ()))
            != {'no-fault', 'delay-100ms', 'loss-10pct', 'combined-stress'}
            or set(event_condition.get('transports', ()))
            != {'redis-pubsub', 'redis-streams'}
        ):
            raise ValueError('event-policy confirmation condition is invalid')

    def digest(self) -> str:
        encoded = json.dumps(
            self.source, sort_keys=True, separators=(',', ':'), allow_nan=False,
        ).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()

    def contains(self, identity: Mapping[str, object]) -> bool:
        return (
            identity.get('stage') == self.partition
            and identity.get('workload') in self.workloads
            and identity.get('regime') in self.regimes
            and identity.get('fault_profile') in self.fault_profiles
            and identity.get('transport') in self.transports
            and isinstance(identity.get('trace_seed'), int)
            and self.seed_start <= identity['trace_seed'] < self.seed_start + self.seed_count
        )
