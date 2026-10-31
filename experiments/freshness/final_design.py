"""Frozen confirmatory final-test campaign contract."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Tuple

from .allocation_design import AllocationDesign
from .analysis_plan import BOOTSTRAP_RESAMPLES, PRIMARY_CONFIDENCE
from .trace_generator import TraceDesign, WORKLOAD_IDS
from .variance_design import PRECISION_OUTCOMES, PRIMARY_FAULT_PROFILES


def load_sample_size_lock(path: Path) -> Mapping:
    value = json.loads(path.read_text(encoding='utf-8'))
    if (
        value.get('measurement_kind') != 'final-test-sample-size-lock'
        or value.get('stage') != 'variance-planning'
        or value.get('confirmatory_final_test') is not False
        or value.get('allow_parameter_changes') is not False
        or value.get('required_final_seeds') != 67
        or value.get('reserved_final_seed_pool') != 20
        or value.get('reserved_pool_sufficient') is not False
        or value.get('status') != 'protocol-expansion-required'
        or value.get('final_test_authorized') is not False
        or value.get('block_count') != 720
        or value.get('full_trace_unit_count') != 5760
    ):
        raise ValueError('invalid or incomplete final sample-size lock')
    return value


@dataclass(frozen=True)
class FinalDesign:
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
    expected_primary_estimates: int

    @classmethod
    def load(
        cls,
        path: Path,
        trace_design: TraceDesign,
        allocation: AllocationDesign,
        sample_size_lock: Mapping,
    ) -> 'FinalDesign':
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
            expected_primary_estimates=value['expected_primary_estimates'],
        )
        design.validate(trace_design, allocation, sample_size_lock)
        return design

    def validate(
        self,
        trace_design: TraceDesign,
        allocation: AllocationDesign,
        sample_size_lock: Mapping,
    ) -> None:
        if self.source.get('schema_version') != 1 or not self.campaign_id:
            raise ValueError('unsupported or unnamed final design')
        if (
            self.source.get('protocol') != 'freshness-protocol-v0.5'
            or self.source.get('trace_design') != trace_design.design_id
            or self.partition != 'final-test'
            or self.source.get('confirmatory_final_test') is not True
            or self.source.get('final_test_authorized') is not True
            or self.source.get('allow_parameter_changes') is not False
            or self.source.get('allow_sample_size_changes') is not False
        ):
            raise ValueError('final-test authorization contract is invalid')
        partition = trace_design.partitions['final-test']
        if (
            self.seed_start != partition['seed_start']
            or self.seed_count != partition['seed_count']
            or self.seed_count != sample_size_lock['required_final_seeds']
        ):
            raise ValueError('final-test seeds differ from the sample-size lock')
        if set(self.workloads) != set(WORKLOAD_IDS):
            raise ValueError('final workloads are incomplete')
        if set(self.regimes) != set(trace_design.regimes):
            raise ValueError('final regimes are incomplete')
        if tuple(self.fault_profiles) != PRIMARY_FAULT_PROFILES:
            raise ValueError('final fault profiles differ from the primary design')
        if set(self.transports) != {'redis-pubsub', 'redis-streams'}:
            raise ValueError('final transports are incomplete')
        if set(self.policies) != set(allocation.policies_per_allocation):
            raise ValueError('final policies differ from the allocation contract')
        contrasts = self.source.get('primary_contrasts', ())
        expected_contrasts = {
            ('repair-vs-invalidate-loss-1pct', 'loss-1pct',
             'event-invalidate-with-repair', 'always-invalidate'),
            ('repair-vs-invalidate-loss-5pct', 'loss-5pct',
             'event-invalidate-with-repair', 'always-invalidate'),
            ('repair-vs-invalidate-loss-10pct', 'loss-10pct',
             'event-invalidate-with-repair', 'always-invalidate'),
            ('write-reactive-vs-update-no-fault', 'no-fault',
             'write-reactive', 'always-update'),
            ('write-reactive-vs-invalidate-no-fault', 'no-fault',
             'write-reactive', 'always-invalidate'),
        }
        observed_contrasts = {
            (
                item.get('contrast_id'), item.get('fault_profile'),
                item.get('treatment'), item.get('reference'),
            )
            for item in contrasts
        }
        if len(contrasts) != 5 or observed_contrasts != expected_contrasts:
            raise ValueError('final primary contrasts differ from the frozen design')
        analysis = self.source.get('analysis', {})
        if (
            tuple(self.source.get('primary_outcomes', ())) != PRECISION_OUTCOMES
            or analysis.get('independent_unit') != (
                'one complete policy execution over one trace'
            )
            or analysis.get('paired_by') != [
                'workload', 'regime', 'transport', 'fault_profile', 'trace_seed',
            ]
            or analysis.get('confidence') != PRIMARY_CONFIDENCE
            or analysis.get('bootstrap_resamples') != BOOTSTRAP_RESAMPLES
            or analysis.get('freshness_admissibility_upper_bound') != 0.01
            or analysis.get('p_values') is not False
            or analysis.get('star_notation') is not False
            or analysis.get('simultaneous_familywise_coverage_claim') is not False
        ):
            raise ValueError('final analysis contract differs from the frozen design')
        block_count = (
            len(self.workloads) * len(self.regimes) * len(self.fault_profiles)
            * len(self.transports) * self.seed_count
        )
        if self.expected_blocks != block_count:
            raise ValueError('final block count is inconsistent')
        if self.expected_full_trace_units != block_count * len(self.policies):
            raise ValueError('final trace-unit count is inconsistent')
        estimate_count = (
            len(self.workloads) * len(self.regimes) * len(self.transports)
            * len(contrasts)
            * len(self.source.get('primary_outcomes', ()))
        )
        if self.expected_primary_estimates != estimate_count:
            raise ValueError('final primary-estimate count is inconsistent')

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
