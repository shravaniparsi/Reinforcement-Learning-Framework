"""Frozen source-bound training campaign and candidate expansion."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence, Tuple

from .parameter_design import ParameterGrid
from .trace_generator import TraceDesign, WORKLOAD_IDS


@dataclass(frozen=True)
class PolicyCandidate:
    candidate_id: str
    policy: str
    options: Mapping[str, Any]
    declared_order: int


@dataclass(frozen=True)
class TrainingCampaign:
    source: Mapping[str, Any]
    parameter_grid: ParameterGrid
    trace_design: TraceDesign

    @classmethod
    def load(
        cls, path: Path, parameter_path: Path, trace_path: Path,
    ) -> 'TrainingCampaign':
        campaign = cls(
            json.loads(path.read_text(encoding='utf-8')),
            ParameterGrid.load(parameter_path),
            TraceDesign.load(trace_path),
        )
        campaign.validate()
        return campaign

    def validate(self) -> None:
        value = self.source
        if value.get('schema_version') != 1 or value.get('campaign_id') != 'freshness-training-campaign-v1':
            raise ValueError('unsupported training campaign')
        if value.get('partition') != 'training' or value.get('final_test_authorized') is not False:
            raise ValueError('training campaign must not authorize final-test collection')
        if tuple(value['workloads']) != WORKLOAD_IDS:
            raise ValueError('training workloads differ from the frozen trace design')
        if tuple(value['regimes']) != tuple(self.trace_design.regimes):
            raise ValueError('training regimes differ from the frozen trace design')
        training = self.trace_design.partitions['training']
        if (value['seed_start'], value['seed_count']) != (
            training['seed_start'], training['seed_count'],
        ):
            raise ValueError('training seed range differs from the frozen partition')
        cost = value['cost_calibration']
        if cost['fault_profile'] != 'no-fault' or cost['transport'] != 'redis-pubsub':
            raise ValueError('cost calibration identity is not canonical')
        if len(cost['policies']) != 8 or set(cost['policies']) != {
            'bypass', 'conditional-validation', 'fixed-ttl', 'stale-while-revalidate',
            'always-invalidate', 'always-update', 'write-reactive',
            'event-invalidate-with-repair',
        }:
            raise ValueError('cost calibration policies are incomplete')
        if tuple(cost['cost_statistics_from']) != (
            'bypass', 'always-invalidate', 'always-update',
        ):
            raise ValueError('cost statistic sources are incomplete')
        time_conditions = value['time_candidate_conditions']
        if (
            time_conditions['fault_profile'] != 'no-fault'
            or time_conditions['transport'] != 'redis-pubsub'
            or tuple(time_conditions['candidate_policies']) != (
                'fixed-ttl', 'stale-while-revalidate',
            )
            or len(time_conditions['matched_controls']) != 6
        ):
            raise ValueError('time candidate conditions differ from the frozen campaign')
        event = value['event_candidate_conditions']
        expected_profiles = ('no-fault', 'delay-100ms', 'loss-10pct', 'combined-stress')
        if tuple(event['fault_profiles']) != expected_profiles:
            raise ValueError('event candidate fault conditions differ from the frozen campaign')
        if tuple(event['transports']) != ('redis-pubsub', 'redis-streams'):
            raise ValueError('event candidate transports are incomplete')
        if tuple(event['candidate_policies']) != (
            'event-invalidate-with-repair', 'write-reactive',
        ) or len(event['matched_controls']) != 6:
            raise ValueError('event candidate policy families are incomplete')
        if any(profile not in self.trace_design.fault_profiles for profile in expected_profiles):
            raise ValueError('campaign references an unknown fault profile')

    def digest(self) -> str:
        encoded = json.dumps(
            self.source, sort_keys=True, separators=(',', ':'), allow_nan=False,
        ).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()

    def candidates(self, policy: str) -> Tuple[PolicyCandidate, ...]:
        candidates = []
        if policy == 'fixed-ttl':
            options = ({'ttl_ms': value} for value in self.parameter_grid.fixed_ttl_ms)
        elif policy == 'stale-while-revalidate':
            options = (
                {'ttl_ms': ttl, 'stale_window_ms': window}
                for ttl in self.parameter_grid.swr_ttl_ms
                for window in self.parameter_grid.stale_window_ms
            )
        elif policy == 'event-invalidate-with-repair':
            options = ({'repair_ms': value} for value in self.parameter_grid.repair_ms)
        elif policy == 'write-reactive':
            options = (
                {'initial_expected_writes': value}
                for value in self.parameter_grid.initial_expected_writes
            )
        else:
            raise ValueError('policy does not have training candidates')
        for order, item in enumerate(options):
            suffix = '-'.join('%s-%s' % (key.replace('_', '-'), item[key]) for key in sorted(item))
            candidates.append(PolicyCandidate('%s:%s' % (policy, suffix), policy, item, order))
        return tuple(candidates)

    def expected_unit_counts(self) -> Mapping[str, int]:
        strata = len(self.source['workloads']) * len(self.source['regimes']) * self.source['seed_count']
        event_conditions = (
            len(self.source['event_candidate_conditions']['fault_profiles'])
            * len(self.source['event_candidate_conditions']['transports'])
        )
        return {
            'cost-calibration': strata * 8,
            'time-candidates': strata * (
                len(self.candidates('fixed-ttl'))
                + len(self.candidates('stale-while-revalidate'))
                + len(self.source['time_candidate_conditions']['matched_controls'])
            ),
            'event-candidates-and-controls': strata * event_conditions * (
                len(self.candidates('event-invalidate-with-repair'))
                + len(self.candidates('write-reactive'))
                + len(self.source['event_candidate_conditions']['matched_controls'])
            ),
        }
