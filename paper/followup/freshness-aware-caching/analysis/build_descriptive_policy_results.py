"""Build descriptive absolute policy summaries from the frozen raw archive.

This is a reporting-only companion to the frozen confirmatory analyzer. It does
not alter the prespecified contrasts or primary results. The input may be a
local uncompressed tar archive or ``-`` for a tar stream on standard input.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import statistics
import sys
import tarfile
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import BinaryIO, Mapping

import numpy as np

from experiments.freshness.analysis_plan import paired_bootstrap_mean_interval
from experiments.freshness.analyze_final_test import _estimate
from experiments.freshness.plan_final_sample_size import _outcome_value


EXPECTED_BLOCKS = 4_824
EXPECTED_POLICIES = (
    'bypass',
    'conditional-validation',
    'fixed-ttl',
    'stale-while-revalidate',
    'always-invalidate',
    'always-update',
    'write-reactive',
    'event-invalidate-with-repair',
)
OUTCOMES = (
    'freshness_violation_proportion',
    'mean_request_wall_ns',
    'operation_thread_cpu_ns',
    'total_origin_response_body_bytes',
    'redis_delivery_payload_bytes',
)


class _HashingReader:
    def __init__(self, source: BinaryIO) -> None:
        self.source = source
        self.digest = hashlib.sha256()

    def read(self, size: int = -1) -> bytes:
        value = self.source.read(size)
        self.digest.update(value)
        return value


def _bootstrap_seed(identity: Mapping) -> int:
    encoded = json.dumps(
        identity, sort_keys=True, separators=(',', ':'), allow_nan=False,
    ).encode('utf-8')
    return int.from_bytes(hashlib.sha256(encoded).digest()[:8], 'big')


def _read_archive(
    source: BinaryIO,
) -> tuple[dict[tuple[str, str, str, str, int, str], dict], str, int]:
    hashing_source = _HashingReader(source)
    summaries: dict[tuple[str, str, str, str, int, str], dict] = {}
    block_identities = set()
    member_count = 0
    with tarfile.open(fileobj=hashing_source, mode='r|') as outer:
        for member in outer:
            if not member.isfile():
                continue
            member_count += 1
            if not member.name.endswith('.zip'):
                raise ValueError(f'unexpected tar member: {member.name}')
            extracted = outer.extractfile(member)
            if extracted is None:
                raise ValueError(f'cannot read tar member: {member.name}')
            archive_bytes = extracted.read()
            with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
                names = [name for name in archive.namelist() if not name.endswith('/')]
                manifests = [name for name in names if name.endswith('/manifest.json')]
                if len(manifests) != 1:
                    raise ValueError('each block archive must contain one manifest')
                manifest = json.loads(archive.read(manifests[0]))
                if (
                    not manifest.get('passed')
                    or manifest.get('measurement_kind') != 'confirmatory-final-test-block'
                    or manifest.get('confirmatory_final_test') is not True
                ):
                    raise ValueError('raw archive contains a failed or non-final block')
                identity = manifest['block_identity']
                block_key = (
                    identity['workload'], identity['regime'],
                    identity['fault_profile'], identity['transport'],
                    int(identity['trace_seed']),
                )
                if block_key in block_identities:
                    raise ValueError(f'duplicate block identity: {block_key}')
                block_identities.add(block_key)
                unit_names = [
                    name for name in names
                    if name.endswith('.json')
                    and '/options/' not in name
                    and not name.endswith('/manifest.json')
                    and not name.endswith('/schedule.json')
                ]
                policies = set()
                for unit_name in unit_names:
                    unit = json.loads(archive.read(unit_name))
                    if (
                        unit.get('measurement_kind') != 'instrumented-freshness-trace-unit'
                        or unit.get('confirmatory_final_test') is not True
                    ):
                        raise ValueError('raw archive contains a non-final unit')
                    summary = unit['summary']
                    policy = summary['policy']
                    policies.add(policy)
                    key = (*block_key, policy)
                    if key in summaries:
                        raise ValueError(f'duplicate policy unit: {key}')
                    summaries[key] = summary
                if policies != set(EXPECTED_POLICIES):
                    raise ValueError(f'incomplete policy set for block {block_key}')
    while hashing_source.read(1024 * 1024):
        pass
    if member_count != EXPECTED_BLOCKS or len(block_identities) != EXPECTED_BLOCKS:
        raise ValueError(
            f'expected {EXPECTED_BLOCKS} complete blocks, found {member_count}'
        )
    if len(summaries) != EXPECTED_BLOCKS * len(EXPECTED_POLICIES):
        raise ValueError('raw archive does not contain every policy execution')
    return summaries, hashing_source.digest.hexdigest(), member_count


def _verify_primary_estimates(
    summaries: Mapping[tuple[str, str, str, str, int, str], Mapping],
    released_analysis: Mapping,
) -> int:
    checked = 0
    for released in released_analysis['primary_estimates']:
        identity = {
            'workload': released['workload'],
            'regime': released['regime'],
            'transport': released['transport'],
            'contrast_id': released['contrast_id'],
            'outcome_id': released['outcome_id'],
        }
        treatment = {}
        reference = {}
        for seed in range(1000, 1067):
            prefix = (
                released['workload'], released['regime'],
                released['fault_profile'], released['transport'], seed,
            )
            treatment[seed] = _outcome_value(
                summaries[(*prefix, released['treatment'])], released['outcome_id'],
            )
            reference[seed] = _outcome_value(
                summaries[(*prefix, released['reference'])], released['outcome_id'],
            )
        observed = _estimate(treatment, reference, identity)
        for field in (
            'estimate', 'lower', 'upper', 'confidence', 'n', 'resamples',
            'paired_mean_ratio', 'consistent_negative_count',
            'consistent_positive_count', 'zero_difference_count',
        ):
            if observed[field] != released[field]:
                raise ValueError(
                    f'primary estimate mismatch for {identity}, field {field}: '
                    f'{observed[field]} != {released[field]}'
                )
        checked += 1
    if checked != 450:
        raise ValueError(f'expected 450 primary estimates, checked {checked}')
    return checked


def _absolute_rows(
    summaries: Mapping[tuple[str, str, str, str, int, str], Mapping],
) -> list[dict]:
    grouped = defaultdict(dict)
    for (workload, regime, fault, transport, seed, policy), summary in summaries.items():
        grouped[workload, regime, fault, transport, policy][seed] = float(
            summary['freshness_violation_proportion']
        )
    rows = []
    for identity, by_seed in sorted(grouped.items()):
        if set(by_seed) != set(range(1000, 1067)):
            raise ValueError(f'incomplete seed set for {identity}')
        values = [by_seed[seed] for seed in sorted(by_seed)]
        interval_identity = {
            'report': 'absolute-policy-freshness',
            'workload': identity[0], 'regime': identity[1],
            'fault_profile': identity[2], 'transport': identity[3],
            'policy': identity[4],
        }
        interval = paired_bootstrap_mean_interval(
            values,
            confidence=0.95,
            resamples=10_000,
            seed=_bootstrap_seed(interval_identity),
        )
        rows.append({
            'workload': identity[0],
            'regime': identity[1],
            'fault_profile': identity[2],
            'transport': identity[3],
            'policy': identity[4],
            'mean_freshness_violation_proportion': interval.estimate,
            'lower_95': interval.lower,
            'upper_95': interval.upper,
            'n_complete_traces': interval.n,
            'resamples': interval.resamples,
        })
    if len(rows) != 576:
        raise ValueError(f'expected 576 absolute policy summaries, found {len(rows)}')
    return rows


def _absolute_outcome_rows(
    summaries: Mapping[tuple[str, str, str, str, int, str], Mapping],
) -> list[dict]:
    grouped = defaultdict(dict)
    for (workload, regime, fault, transport, seed, policy), summary in summaries.items():
        for outcome in OUTCOMES:
            grouped[workload, regime, fault, transport, policy, outcome][seed] = (
                float(_outcome_value(summary, outcome))
            )
    rows = []
    for identity, by_seed in sorted(grouped.items()):
        if set(by_seed) != set(range(1000, 1067)):
            raise ValueError(f'incomplete seed set for {identity}')
        values = [by_seed[seed] for seed in sorted(by_seed)]
        rows.append({
            'workload': identity[0],
            'regime': identity[1],
            'fault_profile': identity[2],
            'transport': identity[3],
            'policy': identity[4],
            'outcome_id': identity[5],
            'mean': statistics.fmean(values),
            'sample_standard_deviation': statistics.stdev(values),
            'minimum': min(values),
            'maximum': max(values),
            'n_complete_traces': len(values),
        })
    if len(rows) != 2_880:
        raise ValueError(f'expected 2,880 outcome summaries, found {len(rows)}')
    return rows


def _main_table_rows(
    absolute_rows: list[Mapping], released_analysis: Mapping,
) -> list[dict]:
    policies = ('always-invalidate', 'event-invalidate-with-repair')
    by_fault_policy = defaultdict(list)
    by_stratum_policy = {}
    for row in absolute_rows:
        if row['policy'] in policies:
            value = float(row['mean_freshness_violation_proportion']) * 100
            by_fault_policy[row['fault_profile'], row['policy']].append(value)
            stratum = (
                row['workload'], row['regime'], row['fault_profile'], row['transport'],
            )
            by_stratum_policy[stratum, row['policy']] = value
    contrast_by_fault = defaultdict(list)
    for row in released_analysis['primary_estimates']:
        if (
            row['outcome_id'] == 'freshness_violation_proportion'
            and row['contrast_id'].startswith('repair-vs-invalidate-')
        ):
            contrast_by_fault[row['fault_profile']].append(float(row['estimate']) * -100)
    rows = []
    for fault in ('no-fault', 'loss-1pct', 'loss-5pct', 'loss-10pct'):
        invalidation = by_fault_policy[fault, 'always-invalidate']
        repair = by_fault_policy[fault, 'event-invalidate-with-repair']
        reductions = contrast_by_fault.get(fault, [])
        if not reductions:
            reductions = [
                by_stratum_policy[stratum, 'always-invalidate']
                - by_stratum_policy[stratum, 'event-invalidate-with-repair']
                for stratum in sorted({
                    key[0] for key in by_stratum_policy
                    if key[0][2] == fault
                })
            ]
        rows.append({
            'fault_profile': fault,
            'always_invalidation_min_percent': min(invalidation),
            'always_invalidation_max_percent': max(invalidation),
            'bounded_repair_min_percent': min(repair),
            'bounded_repair_max_percent': max(repair),
            'paired_reduction_min_percentage_points': min(reductions),
            'paired_reduction_max_percentage_points': max(reductions),
            'strata': len(invalidation),
            'n_complete_traces_per_stratum': 67,
        })
    return rows


def _repair_freshness_familywise_sensitivity(
    summaries: Mapping[tuple[str, str, str, str, int, str], Mapping],
) -> tuple[list[dict], float]:
    """Post hoc 95% familywise upper bounds for 54 repair estimands.

    A common set of resampled seed indices preserves the observed alignment of
    the 67 final-test seed labels across strata. The max statistic uses each
    estimand's observed standard error as its scale; this avoids undefined
    studentized replicates in sparse strata containing many exact zeros.
    """
    strata = sorted({
        (workload, regime, fault, transport)
        for workload, regime, fault, transport, _, _ in summaries
        if fault in {'loss-1pct', 'loss-5pct', 'loss-10pct'}
    })
    if len(strata) != 54:
        raise ValueError(f'expected 54 loss strata, found {len(strata)}')
    paired = []
    for stratum in strata:
        values = []
        for seed in range(1000, 1067):
            prefix = (*stratum, seed)
            treatment = float(summaries[(*prefix, 'event-invalidate-with-repair')][
                'freshness_violation_proportion'
            ])
            reference = float(summaries[(*prefix, 'always-invalidate')][
                'freshness_violation_proportion'
            ])
            values.append(treatment - reference)
        paired.append(np.asarray(values, dtype=float))
    matrix = np.vstack(paired)
    estimates = np.asarray(
        [statistics.fmean(values.tolist()) for values in matrix], dtype=float,
    )
    standard_errors = np.asarray([
        statistics.stdev(values.tolist()) / math.sqrt(matrix.shape[1])
        for values in matrix
    ], dtype=float)
    if np.any(standard_errors <= 0):
        raise ValueError('familywise sensitivity requires positive standard errors')
    resamples = 10_000
    rng = np.random.default_rng(_bootstrap_seed({
        'report': 'repair-freshness-familywise-upper-sensitivity',
        'resamples': resamples,
    }))
    indices = rng.integers(0, matrix.shape[1], size=(resamples, matrix.shape[1]))
    maximum = np.full(resamples, -np.inf)
    for index, values in enumerate(matrix):
        bootstrap_means = np.mean(values[indices], axis=1)
        standardized = (bootstrap_means - estimates[index]) / standard_errors[index]
        maximum = np.maximum(maximum, standardized)
    critical_value = float(np.quantile(maximum, 0.95, method='higher'))
    rows = []
    for stratum, estimate, standard_error in zip(strata, estimates, standard_errors):
        rows.append({
            'workload': stratum[0],
            'regime': stratum[1],
            'fault_profile': stratum[2],
            'transport': stratum[3],
            'paired_mean_difference': float(estimate),
            'observed_standard_error': float(standard_error),
            'familywise_upper_95': float(estimate + critical_value * standard_error),
            'familywise_confidence': 0.95,
            'resamples': resamples,
            'critical_value': critical_value,
        })
    return rows, critical_value


def _write_csv(path: Path, rows: list[Mapping]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('raw_tar', help='uncompressed tar path or - for stdin')
    parser.add_argument('released_analysis', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--expected-tar-sha256', required=True)
    args = parser.parse_args()
    source = sys.stdin.buffer if args.raw_tar == '-' else open(args.raw_tar, 'rb')
    try:
        summaries, tar_digest, block_count = _read_archive(source)
    finally:
        if args.raw_tar != '-':
            source.close()
    if tar_digest != args.expected_tar_sha256:
        raise ValueError(
            f'raw tar SHA-256 mismatch: {tar_digest} != {args.expected_tar_sha256}'
        )
    released = json.loads(args.released_analysis.read_text(encoding='utf-8'))
    checked = _verify_primary_estimates(summaries, released)
    absolute = _absolute_rows(summaries)
    absolute_outcomes = _absolute_outcome_rows(summaries)
    main_table = _main_table_rows(absolute, released)
    sensitivity, sensitivity_critical = _repair_freshness_familywise_sensitivity(summaries)
    args.output.mkdir(parents=True, exist_ok=True)
    _write_csv(args.output / 'absolute_policy_freshness.csv', absolute)
    _write_csv(args.output / 'absolute_policy_outcomes.csv', absolute_outcomes)
    _write_csv(args.output / 'absolute_repair_context.csv', main_table)
    _write_csv(args.output / 'repair_freshness_familywise_sensitivity.csv', sensitivity)
    verification = {
        'measurement_kind': 'descriptive-reporting-verification',
        'raw_tar_sha256': tar_digest,
        'block_count': block_count,
        'policy_execution_count': len(summaries),
        'absolute_summary_count': len(absolute),
        'absolute_outcome_summary_count': len(absolute_outcomes),
        'reproduced_primary_estimate_count': checked,
        'primary_estimates_exactly_reproduced': True,
        'descriptive_interval_confidence': 0.95,
        'descriptive_interval_resamples': 10_000,
        'familywise_sensitivity_estimate_count': len(sensitivity),
        'familywise_sensitivity_confidence': 0.95,
        'familywise_sensitivity_resamples': 10_000,
        'familywise_sensitivity_critical_value': sensitivity_critical,
    }
    (args.output / 'descriptive_verification.json').write_text(
        json.dumps(verification, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )


if __name__ == '__main__':
    main()
