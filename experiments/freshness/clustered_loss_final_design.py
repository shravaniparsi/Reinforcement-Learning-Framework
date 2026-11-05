"""Validated design contract for the prospective clustered-loss final study."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .clustered_loss_design import FAULT_PROFILES
from .trace_generator import TraceDesign, WORKLOAD_IDS


FINAL_STAGE = "extension-final"
FINAL_POLICIES = (
    "conditional-validation",
    "fixed-ttl",
    "always-invalidate",
    "event-invalidate-with-repair",
)


@dataclass(frozen=True)
class ClusteredLossFinalDesign:
    source: Mapping[str, Any]

    @classmethod
    def load(
        cls,
        path: Path,
        base: TraceDesign,
        protocol_path: Path,
    ) -> "ClusteredLossFinalDesign":
        design = cls(json.loads(path.read_text(encoding="utf-8")))
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        design.validate(base, protocol)
        return design

    def validate(self, base: TraceDesign, protocol: Mapping[str, Any]) -> None:
        value = self.source
        if value.get("schema_version") != 1 or not value.get("design_id"):
            raise ValueError("unsupported or unnamed clustered-loss final design")
        if value.get("protocol") != "clustered-loss-protocol-v0.1":
            raise ValueError("unexpected clustered-loss protocol")
        if value.get("final_protocol_id") != protocol.get("protocol_id"):
            raise ValueError("final design names a different final protocol")
        if protocol.get("status") != "authorized-prospective":
            raise ValueError("final protocol is not prospectively authorized")
        if protocol.get("collection_authorized") is not True:
            raise ValueError("final protocol does not authorize collection")
        if value.get("base_trace_design") != base.design_id:
            raise ValueError("final design names a different base trace design")
        if value.get("updates_per_trace") != base.updates_per_trace:
            raise ValueError("final design and base update counts differ")
        if tuple(value.get("fault_profiles", ())) != FAULT_PROFILES:
            raise ValueError("final fault profiles differ from the extension protocol")
        if value.get("stage") != FINAL_STAGE:
            raise ValueError("unexpected final stage")
        start = value.get("seed_start")
        count = value.get("seed_count")
        if (start, count) != (
            protocol.get("final_seed_start"),
            protocol.get("final_seed_count"),
        ):
            raise ValueError("final seed range differs from the authorized protocol")
        if start + count != protocol.get("final_seed_stop_exclusive"):
            raise ValueError("final seed stop differs from the authorized protocol")
        planning = protocol.get("planning_provenance", {})
        planning_seeds = set(
            range(
                planning.get("planning_seed_start", 0),
                planning.get("planning_seed_start", 0)
                + planning.get("planning_seed_count", 0),
            )
        )
        if planning_seeds & set(range(start, start + count)):
            raise ValueError("final seeds overlap precision-planning seeds")
        if (
            value.get("protected_prefix_updates"),
            value.get("protected_suffix_updates"),
            value.get("loss_count"),
        ) != (20, 20, 10):
            raise ValueError("clustered-loss fault budget or guards changed")
        if set(value.get("workloads", ())) != set(WORKLOAD_IDS):
            raise ValueError("final workloads are incomplete")
        if set(value.get("regimes", ())) != set(base.regimes):
            raise ValueError("final regimes are incomplete")
        if set(value.get("transports", ())) != {"redis-pubsub", "redis-streams"}:
            raise ValueError("final transports are incomplete")
        if tuple(value.get("policies", ())) != FINAL_POLICIES:
            raise ValueError("final policy set or order changed")
        if value.get("confirmatory_final_test") is not True:
            raise ValueError("final design is not marked confirmatory")
        if value.get("final_extension_collection") is not True:
            raise ValueError("final extension collection flag is not set")

    def digest(self) -> str:
        encoded = json.dumps(
            self.source,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def contains(self, identity: Mapping[str, Any]) -> bool:
        seed = identity.get("trace_seed")
        return (
            identity.get("stage") == FINAL_STAGE
            and identity.get("workload") in self.source["workloads"]
            and identity.get("regime") in self.source["regimes"]
            and identity.get("fault_profile") in self.source["fault_profiles"]
            and identity.get("transport") in self.source["transports"]
            and isinstance(seed, int)
            and not isinstance(seed, bool)
            and self.source["seed_start"]
            <= seed
            < self.source["seed_start"] + self.source["seed_count"]
        )


__all__ = ["ClusteredLossFinalDesign", "FINAL_POLICIES", "FINAL_STAGE"]
