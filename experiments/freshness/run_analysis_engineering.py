"""Exercise the frozen selection and interval code on synthetic fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from .analysis_plan import (
    CandidateSummary,
    final_trace_requirement,
    paired_bootstrap_mean_interval,
    required_trace_count,
    reserved_pool_is_sufficient,
    select_candidate,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(fixture_path: Path) -> dict:
    fixture = json.loads(fixture_path.read_text(encoding='utf-8'))
    if fixture.get('schema_version') != 1:
        raise ValueError('unsupported analysis fixture version')
    candidates = tuple(CandidateSummary(**item) for item in fixture['candidate_summaries'])
    selected = select_candidate(candidates)
    if selected.name != fixture['expected_selected_candidate']:
        raise AssertionError('engineering candidate selection differs from fixture expectation')

    intervals = {}
    requirements = {}
    for index, (name, differences) in enumerate(
        sorted(fixture['primary_paired_differences'].items())
    ):
        intervals[name] = asdict(paired_bootstrap_mean_interval(
            differences, seed=10_000 + index,
        ))
        requirements[name] = required_trace_count(
            differences, fixture['precision_targets'][name],
        )
    required = final_trace_requirement(requirements.values())
    expansion = not reserved_pool_is_sufficient(required)
    if expansion is not fixture['expected_pool_expansion']:
        raise AssertionError('engineering pool-expansion path differs from fixture expectation')
    return {
        'artifact_schema_version': 1,
        'measurement_kind': 'synthetic-analysis-engineering-only',
        'contains_application_study_observations': False,
        'fixture_id': fixture['fixture_id'],
        'selected_candidate': selected.name,
        'primary_intervals': intervals,
        'trace_requirements': requirements,
        'final_trace_requirement': required,
        'requires_reserved_pool_expansion': expansion,
        'source_sha256': {
            'fixture': _sha256(fixture_path),
            'analysis_plan.py': _sha256(Path(__file__).with_name('analysis_plan.py')),
            'run_analysis_engineering.py': _sha256(Path(__file__)),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument(
        '--fixture', type=Path, default=Path(__file__).with_name('analysis_fixture_v1.json'),
    )
    args = parser.parse_args()
    artifact = run(args.fixture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(artifact, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
