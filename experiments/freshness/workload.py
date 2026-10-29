"""Shared workload and semantic-oracle contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Protocol


def content_hash(content: Any) -> str:
    """Hash complete JSON-compatible content while preserving list order."""
    encoded = json.dumps(
        content, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
        allow_nan=False,
    ).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class CommitRecord:
    revision: int
    committed_at_ms: int
    affected_keys: tuple
    notification_payload: Mapping[str, Any]


@dataclass(frozen=True)
class ReadRecord:
    decision_revision: int
    served_revision: int
    content: Any
    content_sha256: str
    validator: Optional[str]
    origin_read: bool
    response_body_bytes: int
    not_modified: bool = False


@dataclass(frozen=True)
class OracleSnapshot:
    decision_revision: int
    content: Any
    content_sha256: str


class WorkloadAdapter(Protocol):
    workload_id: str

    def reset(self, seed: int) -> None:
        ...

    def commit(self, mutation: Mapping[str, Any], at_ms: int) -> CommitRecord:
        ...

    def read(self, key_or_query: str, validator: Optional[str] = None) -> ReadRecord:
        ...

    def oracle(self, key_or_query: str, decision_revision: int) -> OracleSnapshot:
        ...
