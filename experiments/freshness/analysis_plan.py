"""Prospectively fixed trace-level selection and interval calculations."""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Sequence, Tuple


PRIMARY_CONFIDENCE = 0.99
SECONDARY_CONFIDENCE = 0.95
PRIMARY_Z = 2.5758293035489004
FRESHNESS_MARGIN = 0.01
MIN_FINAL_TRACES = 8
RESERVED_FINAL_TRACES = 20
BOOTSTRAP_RESAMPLES = 10_000


@dataclass(frozen=True)
class CandidateSummary:
    name: str
    mean_freshness_violation: float
    mean_origin_response_bytes: float
    declared_order: int

    def validate(self) -> None:
        if not self.name:
            raise ValueError('candidate name must be non-empty')
        if not 0 <= self.mean_freshness_violation <= 1:
            raise ValueError('freshness violation must be a proportion')
        if self.mean_origin_response_bytes < 0:
            raise ValueError('origin response bytes must be non-negative')
        if not isinstance(self.declared_order, int) or self.declared_order < 0:
            raise ValueError('declared order must be a non-negative integer')


@dataclass(frozen=True)
class IntervalEstimate:
    estimate: float
    lower: float
    upper: float
    confidence: float
    n: int
    resamples: int


def select_candidate(candidates: Sequence[CandidateSummary]) -> CandidateSummary:
    """Apply the frozen lexicographic training rule."""

    if not candidates:
        raise ValueError('parameter selection requires candidates')
    for candidate in candidates:
        candidate.validate()
    names = [candidate.name for candidate in candidates]
    orders = [candidate.declared_order for candidate in candidates]
    if len(names) != len(set(names)) or len(orders) != len(set(orders)):
        raise ValueError('candidate names and declared orders must be unique')
    best_freshness = min(item.mean_freshness_violation for item in candidates)
    eligible = [
        item for item in candidates
        if item.mean_freshness_violation <= best_freshness + FRESHNESS_MARGIN
    ]
    return min(
        eligible,
        key=lambda item: (item.mean_origin_response_bytes, item.declared_order),
    )


def paired_differences(
    treatment: Mapping[str, float], reference: Mapping[str, float]
) -> Tuple[float, ...]:
    """Return one difference per complete paired trace unit."""

    if set(treatment) != set(reference):
        missing_treatment = sorted(set(reference) - set(treatment))
        missing_reference = sorted(set(treatment) - set(reference))
        raise ValueError(
            'paired trace identities differ; '
            f'missing treatment={missing_treatment}, missing reference={missing_reference}'
        )
    if not treatment:
        raise ValueError('paired differences require trace units')
    return tuple(treatment[key] - reference[key] for key in sorted(treatment))


def _nearest_rank(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    rank = max(1, math.ceil(probability * len(ordered)))
    return ordered[min(rank - 1, len(ordered) - 1)]


def paired_bootstrap_mean_interval(
    differences: Sequence[float],
    *,
    confidence: float = PRIMARY_CONFIDENCE,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = 0,
) -> IntervalEstimate:
    """Percentile interval resampling complete paired trace units."""

    values = tuple(float(value) for value in differences)
    if len(values) < 2:
        raise ValueError('bootstrap interval requires at least two trace units')
    if not 0 < confidence < 1 or resamples < 1000:
        raise ValueError('invalid confidence or resample count')
    if any(not math.isfinite(value) for value in values):
        raise ValueError('paired differences must be finite')
    rng = random.Random(seed)
    n = len(values)
    bootstrap_means = []
    for _ in range(resamples):
        bootstrap_means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    alpha = (1 - confidence) / 2
    return IntervalEstimate(
        estimate=statistics.fmean(values),
        lower=_nearest_rank(bootstrap_means, alpha),
        upper=_nearest_rank(bootstrap_means, 1 - alpha),
        confidence=confidence,
        n=n,
        resamples=resamples,
    )


def required_trace_count(
    paired_differences_for_planning: Sequence[float],
    target_half_width: float,
    *,
    z_value: float = PRIMARY_Z,
    minimum: int = MIN_FINAL_TRACES,
) -> int:
    """Normal-approximation precision planning from paired planning traces."""

    values = tuple(float(value) for value in paired_differences_for_planning)
    if len(values) < 2 or target_half_width <= 0 or z_value <= 0 or minimum < 2:
        raise ValueError('invalid precision-planning inputs')
    if any(not math.isfinite(value) for value in values):
        raise ValueError('planning differences must be finite')
    standard_deviation = statistics.stdev(values)
    calculated = math.ceil((z_value * standard_deviation / target_half_width) ** 2)
    return max(minimum, calculated)


def final_trace_requirement(requirements: Iterable[int]) -> int:
    values = tuple(requirements)
    if not values or any(not isinstance(value, int) or value < 2 for value in values):
        raise ValueError('trace requirements must be integers of at least two')
    return max(values)


def reserved_pool_is_sufficient(required: int) -> bool:
    if not isinstance(required, int) or required < 2:
        raise ValueError('required trace count must be an integer of at least two')
    return required <= RESERVED_FINAL_TRACES
