"""Build manuscript tables and figures from the frozen primary analysis."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import matplotlib.pyplot as plt


WORKLOAD_LABELS = {
    'mutable-product-v1': 'Product',
    'svelte-realworld-feed-v1': 'Article feed',
    'react-admin-dashboard-v1': 'Dashboard',
}
REGIME_LABELS = {
    'read-heavy': 'read-heavy',
    'balanced': 'balanced',
    'write-intensive': 'write-intensive',
}
WORKLOAD_COLORS = {
    'mutable-product-v1': '#C96144',
    'svelte-realworld-feed-v1': '#5185C0',
    'react-admin-dashboard-v1': '#55966B',
}
TRANSPORT_MARKERS = {'redis-pubsub': 'o', 'redis-streams': 's'}
TRANSPORT_OFFSETS = {'redis-pubsub': -0.12, 'redis-streams': 0.12}
ROW_ORDER = tuple(
    (workload, regime)
    for workload in WORKLOAD_LABELS
    for regime in REGIME_LABELS
)


def _load(path: Path) -> list[Mapping]:
    value = json.loads(path.read_text(encoding='utf-8'))
    if (
        value.get('measurement_kind') != 'confirmatory-final-analysis'
        or value.get('block_count') != 4824
        or value.get('full_trace_unit_count') != 38592
        or value.get('primary_estimate_count') != 450
        or value.get('p_values_reported') is not False
    ):
        raise ValueError('input is not the complete frozen primary analysis')
    estimates = value['primary_estimates']
    if len(estimates) != 450 or {item['n'] for item in estimates} != {67}:
        raise ValueError('primary estimates do not contain 67 complete paired traces')
    return estimates


def _write_estimates(path: Path, estimates: Sequence[Mapping]) -> None:
    fields = (
        'workload', 'regime', 'transport', 'fault_profile', 'contrast_id',
        'treatment', 'reference', 'outcome_id', 'estimate', 'lower', 'upper',
        'confidence', 'n', 'resamples', 'paired_mean_ratio',
        'consistent_negative_count', 'consistent_positive_count',
        'zero_difference_count', 'efficiency_interpretation_authorized',
    )
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(estimates)


def _write_summary(path: Path, estimates: Sequence[Mapping]) -> None:
    groups = defaultdict(list)
    for item in estimates:
        groups[item['contrast_id'], item['outcome_id']].append(item)
    fields = (
        'contrast_id', 'outcome_id', 'strata', 'estimate_min', 'estimate_max',
        'interval_below_zero', 'interval_above_zero', 'interval_includes_zero',
        'ratio_min', 'ratio_max',
    )
    rows = []
    for (contrast, outcome), items in sorted(groups.items()):
        ratios = [item['paired_mean_ratio'] for item in items
                  if item['paired_mean_ratio'] is not None]
        rows.append({
            'contrast_id': contrast,
            'outcome_id': outcome,
            'strata': len(items),
            'estimate_min': min(item['estimate'] for item in items),
            'estimate_max': max(item['estimate'] for item in items),
            'interval_below_zero': sum(item['upper'] < 0 for item in items),
            'interval_above_zero': sum(item['lower'] > 0 for item in items),
            'interval_includes_zero': sum(
                item['lower'] <= 0 <= item['upper'] for item in items
            ),
            'ratio_min': min(ratios) if ratios else '',
            'ratio_max': max(ratios) if ratios else '',
        })
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _configure_plotting() -> None:
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.size': 7,
        'axes.titlesize': 8,
        'axes.labelsize': 7,
        'axes.linewidth': 0.8,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'legend.frameon': False,
        'svg.fonttype': 'none',
        'pdf.fonttype': 42,
    })


def _row_label(row: tuple[str, str]) -> str:
    return f'{WORKLOAD_LABELS[row[0]]}, {REGIME_LABELS[row[1]]}'


def _forest(
    axis,
    items: Iterable[Mapping],
    *,
    scale: float,
    xlabel: str,
    show_labels: bool,
) -> None:
    by_identity = {
        (item['workload'], item['regime'], item['transport']): item
        for item in items
    }
    for index, row in enumerate(ROW_ORDER):
        for transport in TRANSPORT_MARKERS:
            item = by_identity[row[0], row[1], transport]
            y = len(ROW_ORDER) - 1 - index + TRANSPORT_OFFSETS[transport]
            estimate = item['estimate'] * scale
            lower = item['lower'] * scale
            upper = item['upper'] * scale
            axis.errorbar(
                estimate, y,
                xerr=[[estimate - lower], [upper - estimate]],
                fmt=TRANSPORT_MARKERS[transport],
                color=WORKLOAD_COLORS[row[0]],
                markersize=3.3,
                elinewidth=0.8,
                capsize=1.5,
                markeredgewidth=0.5,
            )
    axis.axvline(0, color='#666666', linewidth=0.7, linestyle=':')
    axis.set_ylim(-0.6, len(ROW_ORDER) - 0.4)
    axis.set_yticks(range(len(ROW_ORDER)))
    axis.set_yticklabels(
        [_row_label(row) for row in reversed(ROW_ORDER)] if show_labels else [],
    )
    axis.set_xlabel(xlabel)
    axis.grid(axis='x', color='#DDDDDD', linewidth=0.5)


def _figure_repair(path: Path, estimates: Sequence[Mapping]) -> None:
    outcomes = (
        ('freshness_violation_proportion', 100.0, 'Freshness difference (percentage points)'),
        ('mean_request_wall_ns', 1e-3, 'Request wall-time difference (µs)'),
    )
    losses = (
        ('repair-vs-invalidate-loss-1pct', '1% notification loss'),
        ('repair-vs-invalidate-loss-5pct', '5% notification loss'),
        ('repair-vs-invalidate-loss-10pct', '10% notification loss'),
    )
    fig, axes = plt.subplots(3, 2, figsize=(7.20, 6.25))
    for row_index, (contrast, loss_label) in enumerate(losses):
        for column_index, (outcome, scale, xlabel) in enumerate(outcomes):
            items = [
                item for item in estimates
                if item['contrast_id'] == contrast and item['outcome_id'] == outcome
            ]
            _forest(
                axes[row_index, column_index], items,
                scale=scale, xlabel=xlabel, show_labels=column_index == 0,
            )
            axes[row_index, column_index].set_title(
                f'{loss_label}\n{("Freshness" if column_index == 0 else "Request time")}'
            )
    handles = [
        plt.Line2D([], [], marker='o', linestyle='none',
                   color=WORKLOAD_COLORS[workload], markersize=4, label=label)
        for workload, label in WORKLOAD_LABELS.items()
    ] + [
        plt.Line2D([], [], marker=TRANSPORT_MARKERS[transport], linestyle='none',
                   color='#333333', markersize=4, label=label)
        for transport, label in (
            ('redis-pubsub', 'Redis Pub/Sub'), ('redis-streams', 'Redis Streams'),
        )
    ]
    fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, 0.95), ncol=5)
    fig.suptitle(
        'Bounded repair reduces freshness violations while increasing request time',
        fontsize=9, y=0.99,
    )
    fig.subplots_adjust(left=0.27, right=0.98, bottom=0.08, top=0.87,
                        hspace=0.68, wspace=0.36)
    for suffix in ('svg', 'pdf', 'png'):
        fig.savefig(path.with_suffix(f'.{suffix}'), dpi=300, bbox_inches='tight')
    plt.close(fig)


def _figure_write_reactive(path: Path, estimates: Sequence[Mapping]) -> None:
    outcomes = (
        ('mean_request_wall_ns', 1e-3, 'Request wall time (µs)'),
        ('operation_thread_cpu_ns', 1e-6, 'Thread CPU per trace (ms)'),
        ('total_origin_response_body_bytes', 1 / 1024, 'Origin body bytes (KiB)'),
        ('redis_delivery_payload_bytes', 1 / 1024, 'Redis payload (KiB)'),
    )
    contrasts = (
        ('write-reactive-vs-update-no-fault', 'Write-reactive minus always update'),
        ('write-reactive-vs-invalidate-no-fault', 'Write-reactive minus always invalidate'),
    )
    fig, axes = plt.subplots(2, 4, figsize=(7.20, 4.95))
    for row_index, (contrast, contrast_label) in enumerate(contrasts):
        for column_index, (outcome, scale, xlabel) in enumerate(outcomes):
            items = [
                item for item in estimates
                if item['contrast_id'] == contrast and item['outcome_id'] == outcome
            ]
            _forest(
                axes[row_index, column_index], items,
                scale=scale, xlabel=xlabel, show_labels=column_index == 0,
            )
            short_contrast = (
                'vs always update' if row_index == 0 else 'vs always invalidate'
            )
            short_outcome = (
                'Request time', 'Thread CPU', 'Origin bytes', 'Redis payload'
            )[column_index]
            axes[row_index, column_index].set_title(
                f'{short_contrast}\n{short_outcome}', fontsize=7.5,
            )
    handles = []
    for workload, label in WORKLOAD_LABELS.items():
        handles.append(plt.Line2D([], [], marker='o', linestyle='none',
                                  color=WORKLOAD_COLORS[workload], markersize=4,
                                  label=label))
    for transport, label in (
        ('redis-pubsub', 'Pub/Sub'), ('redis-streams', 'Streams'),
    ):
        handles.append(plt.Line2D([], [], marker=TRANSPORT_MARKERS[transport],
                                  linestyle='none', color='#333333', markersize=4,
                                  label=label))
    fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, 0.94), ncol=5)
    fig.suptitle(
        'Write-reactive selection shifts costs without a universal fixed-policy gain',
        fontsize=9, y=0.99,
    )
    fig.subplots_adjust(left=0.25, right=0.99, bottom=0.10, top=0.85,
                        hspace=0.58, wspace=0.42)
    for suffix in ('svg', 'pdf', 'png'):
        fig.savefig(path.with_suffix(f'.{suffix}'), dpi=300, bbox_inches='tight')
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('analysis', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    estimates = _load(args.analysis)
    _write_estimates(args.output / 'primary_estimates.csv', estimates)
    _write_summary(args.output / 'primary_contrast_summary.csv', estimates)
    _configure_plotting()
    _figure_repair(args.output / 'figure_1_repair_tradeoffs', estimates)
    _figure_write_reactive(args.output / 'figure_2_write_reactive_tradeoffs', estimates)


if __name__ == '__main__':
    main()
