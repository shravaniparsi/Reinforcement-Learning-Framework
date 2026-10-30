"""Validation for the prospectively declared policy-parameter candidates."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Tuple


@dataclass(frozen=True)
class ParameterGrid:
    grid_id: str
    fixed_ttl_ms: Tuple[int, ...]
    swr_ttl_ms: Tuple[int, ...]
    stale_window_ms: Tuple[int, ...]
    repair_ms: Tuple[int, ...]
    initial_expected_writes: Tuple[float, ...]
    cost_basis: str
    cost_sources: Mapping[str, str]
    selection_partitions: Mapping[str, str]
    source_mapping: Mapping
    schema_version: int = 1

    @classmethod
    def load(cls, path: Path) -> 'ParameterGrid':
        value = json.loads(path.read_text(encoding='utf-8'))
        write = value['write_reactive']
        grid = cls(
            grid_id=value['grid_id'],
            fixed_ttl_ms=tuple(value['fixed_ttl_ms']),
            swr_ttl_ms=tuple(value['stale_while_revalidate']['ttl_ms']),
            stale_window_ms=tuple(value['stale_while_revalidate']['stale_window_ms']),
            repair_ms=tuple(value['repair_ms']),
            initial_expected_writes=tuple(write['initial_expected_writes']),
            cost_basis=write['cost_basis'],
            cost_sources={
                'update': write['update_cost_source'],
                'invalidate': write['invalidate_cost_source'],
                'miss': write['miss_cost_source'],
            },
            selection_partitions=value['selection_partitions'],
            source_mapping=value,
            schema_version=value.get('schema_version', 1),
        )
        grid.validate()
        return grid

    def validate(self) -> None:
        if self.schema_version != 1 or not self.grid_id:
            raise ValueError('unsupported or unnamed parameter grid')
        expected_times = (10, 25, 50, 100, 250, 500)
        if self.fixed_ttl_ms != expected_times:
            raise ValueError('fixed TTL candidates differ from the frozen grid')
        if self.swr_ttl_ms != expected_times or self.stale_window_ms != expected_times:
            raise ValueError('SWR candidates differ from the frozen grid')
        if self.repair_ms != expected_times:
            raise ValueError('repair candidates differ from the frozen grid')
        if self.initial_expected_writes != (0.25, 0.5, 1.0, 2.0, 5.0, 10.0):
            raise ValueError('initial E[W] candidates differ from the frozen grid')
        if self.cost_basis != 'serialized-bytes':
            raise ValueError('write-reactive cost basis must remain serialized bytes')
        if set(self.cost_sources) != {'update', 'invalidate', 'miss'}:
            raise ValueError('write-reactive cost sources are incomplete')
        expected_partitions = {
            'fit': 'training',
            'confirm': 'validation',
            'variance_only': 'variance-planning',
            'locked_evaluation': 'final-test',
        }
        if dict(self.selection_partitions) != expected_partitions:
            raise ValueError('parameter-selection partitions are not isolated')

    def digest(self) -> str:
        encoded = json.dumps(
            self.source_mapping, sort_keys=True, separators=(',', ':'), allow_nan=False,
        ).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()
