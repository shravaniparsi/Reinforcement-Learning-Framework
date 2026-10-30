"""Hosted-allocation blocking and policy-order contract."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Tuple

from .cache_gateway import POLICIES


@dataclass(frozen=True)
class AllocationDesign:
    design_id: str
    runner: str
    python_version: str
    redis_package_version: str
    max_parallel_allocations: int
    allocation_block: Tuple[str, ...]
    policies_per_allocation: Tuple[str, ...]
    policy_order_rule: str
    process_isolation: str
    application_failure_retries: int
    infrastructure_failure_retries: int
    retain_all_attempts: bool
    source_mapping: Mapping
    schema_version: int = 1

    @classmethod
    def load(cls, path: Path) -> 'AllocationDesign':
        value = json.loads(path.read_text(encoding='utf-8'))
        design = cls(
            design_id=value['design_id'],
            runner=value['runner'],
            python_version=value['python_version'],
            redis_package_version=value['redis_package_version'],
            max_parallel_allocations=value['max_parallel_allocations'],
            allocation_block=tuple(value['allocation_block']),
            policies_per_allocation=tuple(value['policies_per_allocation']),
            policy_order_rule=value['policy_order'],
            process_isolation=value['process_isolation'],
            application_failure_retries=value['application_failure_retries'],
            infrastructure_failure_retries=value['infrastructure_failure_retries'],
            retain_all_attempts=value['retain_all_attempts'],
            source_mapping=value,
            schema_version=value.get('schema_version', 1),
        )
        design.validate()
        return design

    def validate(self) -> None:
        if self.schema_version != 1 or not self.design_id:
            raise ValueError('unsupported or unnamed allocation design')
        if self.runner != 'ubuntu-24.04' or self.python_version != '3.9.25':
            raise ValueError('hosted runtime differs from the frozen design')
        if self.redis_package_version != '5:7.0.15-1ubuntu0.24.04.5':
            raise ValueError('Redis package differs from the calibrated hosted runtime')
        if not 1 <= self.max_parallel_allocations <= 3:
            raise ValueError('max parallel allocations must remain from one to three')
        required_block = {
            'stage', 'workload', 'regime', 'trace_seed', 'transport', 'fault_profile',
        }
        if set(self.allocation_block) != required_block:
            raise ValueError('allocation block fields are incomplete')
        if set(self.policies_per_allocation) != set(POLICIES):
            raise ValueError('every allocation must execute all declared policies')
        if len(self.policies_per_allocation) != len(POLICIES):
            raise ValueError('allocation policy list contains duplicates')
        if self.application_failure_retries != 0 or self.infrastructure_failure_retries != 1:
            raise ValueError('retry rules differ from the frozen design')
        if not self.retain_all_attempts:
            raise ValueError('all allocation attempts must be retained')

    def digest(self) -> str:
        encoded = json.dumps(
            self.source_mapping, sort_keys=True, separators=(',', ':'), allow_nan=False,
        ).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()

    def policy_order(self, block_identity: Mapping[str, object]) -> Tuple[str, ...]:
        if set(block_identity) != set(self.allocation_block):
            raise ValueError('policy-order identity does not match the allocation block')
        encoded = json.dumps(
            block_identity, sort_keys=True, separators=(',', ':'), allow_nan=False,
        ).encode('utf-8')
        seed = int.from_bytes(hashlib.sha256(encoded).digest()[:8], 'big')
        order = list(self.policies_per_allocation)
        random.Random(seed).shuffle(order)
        return tuple(order)
