"""Frozen variance-planning campaign and precision contract."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Tuple

from .allocation_design import AllocationDesign
from .analysis_plan import MIN_FINAL_TRACES, PRIMARY_CONFIDENCE, PRIMARY_Z, RESERVED_FINAL_TRACES
from .trace_generator import TraceDesign, WORKLOAD_IDS


PRIMARY_FAULT_PROFILES = ('no-fault', 'loss-1pct', 'loss-5pct', 'loss-10pct')
PRECISION_OUTCOMES = (
    'freshness_violation_proportion',
    'mean_request_wall_ns',
    'operation_thread_cpu_ns',
    'total_origin_response_body_bytes',
    'redis_delivery_payload_bytes',
)


def load_passed_validation(path: Path) -> Mapping:
    value = json.loads(path.read_text(encoding='utf-8'))
    if (
        value.get('measurement_kind') != 'held-out-parameter-validation-report'
        or value.get('stage') != 'validation'
        or value.get('confirmatory_final_test') is not False
        or value.get('allow_refitting') is not False
        or value.get('passed') is not True
        or value.get('block_count') != 1080
        or value.get('full_trace_unit_count') != 8640
    ):
        raise ValueError('variance planning requires the complete passed validation lock')
    return value


@dataclass(frozen=True)
class VarianceDesign:
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
    expected_precision_calculations: int

    @classmethod
    def load(
        cls,
        path: Path,
        trace_design: TraceDesign,
        allocation: AllocationDesign,
    ) -> 'VarianceDesign':
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
            expected_precision_calculations=value['expected_precision_calculations'],
        )
        design.validate(trace_design, allocation)
        return design

    def validate(self, trace_design: TraceDesign, allocation: AllocationDesign) -> None:
        if self.source.get('schema_version') != 1 or not self.campaign_id:
            raise ValueError('unsupported or unnamed variance design')
        if (
            self.partition != 'variance-planning'
            or self.source.get('allow_parameter_changes') is not False
            or self.source.get('final_test_authorized') is not False
        ):
            raise ValueError('variance design has an invalid evidence partition')
        partition = trace_design.partitions['variance-planning']
        if (
            self.seed_start != partition['seed_start']
            or self.seed_count != partition['seed_count']
        ):
            raise ValueError('variance seeds differ from the frozen trace partition')
        if set(self.workloads) != set(WORKLOAD_IDS):
            raise ValueError('variance workloads are incomplete')
        if set(self.regimes) != set(trace_design.regimes):
            raise ValueError('variance regimes are incomplete')
        if tuple(self.fault_profiles) != PRIMARY_FAULT_PROFILES:
            raise ValueError('variance fault profiles differ from the primary contrasts')
        if set(self.transports) != {'redis-pubsub', 'redis-streams'}:
            raise ValueError('variance transports are incomplete')
        if set(self.policies) != set(allocation.policies_per_allocation):
            raise ValueError('variance policies differ from the allocation contract')
        contrasts = self.source.get('primary_contrasts', ())
        expected_contrasts = {
            ('loss-1pct', 'event-invalidate-with-repair', 'always-invalidate'),
            ('loss-5pct', 'event-invalidate-with-repair', 'always-invalidate'),
            ('loss-10pct', 'event-invalidate-with-repair', 'always-invalidate'),
            ('no-fault', 'write-reactive', 'always-update'),
            ('no-fault', 'write-reactive', 'always-invalidate'),
        }
        observed_contrasts = {
            (item['fault_profile'], item['treatment'], item['reference'])
            for item in contrasts
        }
        if len(contrasts) != 5 or observed_contrasts != expected_contrasts:
            raise ValueError('variance primary contrasts are incomplete')
        outcomes = self.source.get('precision_outcomes', ())
        if tuple(item['outcome_id'] for item in outcomes) != PRECISION_OUTCOMES:
            raise ValueError('variance precision outcomes are incomplete')
        if outcomes[0] != {
            'outcome_id': 'freshness_violation_proportion',
            'target_kind': 'absolute',
            'target_value': 0.01,
        } or any(
            item['target_kind'] != 'reference_fraction' or item['target_value'] != 0.10
            for item in outcomes[1:]
        ):
            raise ValueError('variance precision targets differ from the frozen rule')
        precision = self.source.get('precision_rule', {})
        if (
            precision.get('confidence') != PRIMARY_CONFIDENCE
            or precision.get('z_value') != PRIMARY_Z
            or precision.get('minimum_final_seeds') != MIN_FINAL_TRACES
            or precision.get('reserved_final_seeds') != RESERVED_FINAL_TRACES
        ):
            raise ValueError('variance precision constants differ from the analysis plan')
        block_count = (
            len(self.workloads) * len(self.regimes) * len(self.fault_profiles)
            * len(self.transports) * self.seed_count
        )
        if self.expected_blocks != block_count:
            raise ValueError('variance block count is inconsistent')
        if self.expected_full_trace_units != block_count * len(self.policies):
            raise ValueError('variance trace-unit count is inconsistent')
        calculation_count = (
            len(self.workloads) * len(self.regimes) * len(self.transports)
            * len(contrasts) * len(outcomes)
        )
        if self.expected_precision_calculations != calculation_count:
            raise ValueError('variance precision-calculation count is inconsistent')

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
