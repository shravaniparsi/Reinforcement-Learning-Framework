"""Verify precision-planning archives and select a final seed count.

The script reports variance and projected interval widths, not pilot effect
directions. Engineering, planning and final observations remain separate.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import re
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

from scipy.stats import chi2, t


WORKLOADS = (
    "mutable-product-v1",
    "react-admin-dashboard-v1",
    "svelte-realworld-feed-v1",
)
REGIMES = ("balanced", "read-heavy", "write-intensive")
TRANSPORTS = ("redis-pubsub", "redis-streams")
PROFILES = ("dispersed-10", "single-burst-10")
POLICIES = ("event-invalidate-with-repair", "always-invalidate")
PROTOCOL = "clustered-loss-protocol-v0.1"
STAGE = "extension-precision-planning"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_plan(path: Path) -> Mapping[str, Any]:
    plan = json.loads(path.read_text(encoding="utf-8"))
    if plan.get("schema_version") != 1:
        raise ValueError("unsupported precision-plan schema")
    if plan.get("protocol") != PROTOCOL or plan.get("planning_stage") != STAGE:
        raise ValueError("precision plan names the wrong protocol or stage")
    if plan.get("independent_unit") != "trace_seed" or plan.get("strata_per_seed") != 18:
        raise ValueError("precision plan changed the independent unit or crossed design")
    if plan.get("final_collection_authorized") is not False:
        raise ValueError("precision planning cannot authorize final collection")
    candidates = plan.get("candidate_final_seed_counts")
    if not candidates or candidates != sorted(set(candidates)):
        raise ValueError("candidate final seed counts must be unique and increasing")
    return plan


def _artifact_name_pattern(run_id: str) -> re.Pattern[str]:
    parts = (
        "clustered-loss-precision-"
        "(mutable-product-v1|react-admin-dashboard-v1|svelte-realworld-feed-v1)-"
        "(balanced|read-heavy|write-intensive)-"
        "(redis-pubsub|redis-streams)-"
        "(210[0-9])-" + re.escape(run_id) + r"\.zip"
    )
    return re.compile("^" + parts + "$")


def _read_results(
    archive_dir: Path, run_id: str, plan: Mapping[str, Any]
) -> Tuple[Mapping[Tuple[int, str, str, str, str, str], Mapping[str, Any]], Mapping[str, Any]]:
    archives = sorted(archive_dir.glob("*.zip"))
    expected_seeds = tuple(
        range(plan["planning_seed_start"], plan["planning_seed_start"] + plan["planning_seed_count"])
    )
    expected_outer = set(itertools.product(WORKLOADS, REGIMES, TRANSPORTS, expected_seeds))
    if len(archives) != len(expected_outer):
        raise ValueError(f"expected {len(expected_outer)} archives, found {len(archives)}")

    pattern = _artifact_name_pattern(run_id)
    outer = set()
    rows: Dict[Tuple[int, str, str, str, str, str], Mapping[str, Any]] = {}
    manifest_count = 0
    artifact_count = 0
    archive_digests = {}
    for archive in archives:
        match = pattern.match(archive.name)
        if not match:
            raise ValueError(f"unexpected archive name: {archive.name}")
        workload, regime, transport, seed_text = match.groups()
        seed = int(seed_text)
        identity = (workload, regime, transport, seed)
        if identity in outer:
            raise ValueError(f"duplicate archive identity: {identity}")
        outer.add(identity)
        archive_digests[archive.name] = _sha256(archive)
        with zipfile.ZipFile(archive) as zipped:
            failed_member = zipped.testzip()
            if failed_member:
                raise ValueError(f"CRC failure in {archive.name}: {failed_member}")
            base = f"{workload}-{regime}-{transport}-{seed}"
            for profile in ("no-fault", "dispersed-10", "single-burst-10", "repeated-bursts-10"):
                prefix = f"{base}/{profile}/"
                manifest = json.loads(zipped.read(prefix + "manifest.json"))
                manifest_count += 1
                block = manifest.get("block_identity", {})
                expected_block = {
                    "stage": STAGE,
                    "workload": workload,
                    "regime": regime,
                    "transport": transport,
                    "trace_seed": seed,
                    "fault_profile": profile,
                }
                if block != expected_block:
                    raise ValueError(f"block identity mismatch in {archive.name}/{profile}")
                if not manifest.get("passed"):
                    raise ValueError(f"failed manifest in {archive.name}/{profile}")
                if manifest.get("protocol") != PROTOCOL or manifest.get("stage") != STAGE:
                    raise ValueError(f"protocol or stage mismatch in {archive.name}/{profile}")
                if manifest.get("confirmatory_final_test") is not False:
                    raise ValueError("precision artifact marked as confirmatory final test")
                if manifest.get("final_extension_collection") is not False:
                    raise ValueError("precision artifact marked as final extension collection")
                attempts = manifest.get("attempts", [])
                if len(attempts) != 4 or any(item.get("returncode") != 0 for item in attempts):
                    raise ValueError(f"incomplete policy attempts in {archive.name}/{profile}")
                for attempt in attempts:
                    policy = attempt["policy"]
                    result = json.loads(zipped.read(prefix + attempt["artifact"]))
                    artifact_count += 1
                    if result.get("protocol") != PROTOCOL or result.get("stage") != STAGE:
                        raise ValueError(f"result protocol or stage mismatch in {archive.name}")
                    if result.get("confirmatory_final_test") is not False:
                        raise ValueError("precision result marked as confirmatory final test")
                    if result.get("final_extension_collection") is not False:
                        raise ValueError("precision result marked as final extension collection")
                    summary = result["summary"]
                    if summary.get("policy") != policy:
                        raise ValueError(f"policy mismatch in {archive.name}/{profile}")
                    for digest_name in ("trace_sha256", "fault_sha256", "schedule_sha256"):
                        if summary.get(digest_name) != manifest.get(digest_name):
                            raise ValueError(f"{digest_name} mismatch in {archive.name}/{profile}")
                    if profile in PROFILES and policy in POLICIES:
                        key = (seed, workload, regime, transport, profile, policy)
                        if key in rows:
                            raise ValueError(f"duplicate result identity: {key}")
                        rows[key] = summary

    if outer != expected_outer:
        raise ValueError("precision archive factorial is incomplete")
    expected_rows = len(expected_outer) * len(PROFILES) * len(POLICIES)
    if len(rows) != expected_rows:
        raise ValueError(f"expected {expected_rows} analysis rows, found {len(rows)}")
    integrity = {
        "archives": len(archives),
        "manifests": manifest_count,
        "policy_results": artifact_count,
        "analysis_rows": len(rows),
        "archive_sha256": archive_digests,
    }
    return rows, integrity


def _seed_estimates(
    rows: Mapping[Tuple[int, str, str, str, str, str], Mapping[str, Any]],
    seeds: Iterable[int],
    recovery_horizon: int,
) -> Mapping[str, Sequence[float]]:
    by_metric: Dict[str, list[float]] = defaultdict(list)
    strata = tuple(itertools.product(WORKLOADS, REGIMES, TRANSPORTS))
    for seed in seeds:
        policy_deltas: Dict[str, Dict[str, float]] = {}
        for policy in POLICIES:
            freshness = []
            persistence = []
            for workload, regime, transport in strata:
                values = {}
                for profile in PROFILES:
                    summary = rows[(seed, workload, regime, transport, profile, policy)]
                    values[profile] = {
                        "freshness": float(summary["freshness_violation_proportion"]),
                        "persistence": float(
                            bool(summary["terminal_recovery_right_censored"])
                            or int(summary["requests_until_observed_terminal_recovery"]) > recovery_horizon
                        ),
                    }
                freshness.append(values["single-burst-10"]["freshness"] - values["dispersed-10"]["freshness"])
                persistence.append(values["single-burst-10"]["persistence"] - values["dispersed-10"]["persistence"])
            policy_deltas[policy] = {
                "freshness": statistics.fmean(freshness),
                "persistence": statistics.fmean(persistence),
            }
        repair = policy_deltas["event-invalidate-with-repair"]
        reference = policy_deltas["always-invalidate"]
        by_metric["repair_profile_freshness"].append(repair["freshness"])
        by_metric["repair_vs_always_freshness_interaction"].append(
            repair["freshness"] - reference["freshness"]
        )
        by_metric["repair_profile_persistence10"].append(repair["persistence"])
        by_metric["repair_vs_always_persistence10_interaction"].append(
            repair["persistence"] - reference["persistence"]
        )
    return by_metric


def _project_widths(values: Sequence[float], candidates: Sequence[int], confidence: float, upper: float) -> Mapping[str, Any]:
    if len(values) < 3:
        raise ValueError("at least three planning seeds are required")
    sample_sd = statistics.stdev(values)
    if sample_sd == 0:
        return {"planning_seed_count": len(values), "sample_sd": 0.0, "stable": False, "projected_full_width": {}}
    df = len(values) - 1
    sigma_upper = math.sqrt(df * sample_sd * sample_sd / chi2.ppf(1.0 - upper, df))
    widths = {
        str(candidate): 2.0 * t.ppf((1.0 + confidence) / 2.0, candidate - 1) * sigma_upper / math.sqrt(candidate)
        for candidate in candidates
    }
    return {
        "planning_seed_count": len(values),
        "sample_sd": sample_sd,
        "upper_sd_confidence": upper,
        "upper_sd_bound": sigma_upper,
        "stable": True,
        "projected_full_width": widths,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive_dir", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--plan",
        type=Path,
        default=Path("experiments/freshness/clustered_loss_precision_plan_v1.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    plan = _load_plan(args.plan)
    rows, integrity = _read_results(args.archive_dir, args.run_id, plan)
    seeds = range(plan["planning_seed_start"], plan["planning_seed_start"] + plan["planning_seed_count"])
    estimates = _seed_estimates(rows, seeds, plan["recovery_horizon_requests"])
    candidates = plan["candidate_final_seed_counts"]
    projections = {
        metric: _project_widths(
            values, candidates, plan["confidence_level"], plan["variance_upper_confidence"]
        )
        for metric, values in estimates.items()
    }
    targets = plan["precision_targets_full_width"]
    selected = None
    if all(item["stable"] for item in projections.values()):
        for candidate in candidates:
            if all(item["projected_full_width"][str(candidate)] <= targets[metric] for metric, item in projections.items()):
                selected = candidate
                break
    report = {
        "analysis": "clustered-loss-precision-planning-v1",
        "protocol": PROTOCOL,
        "stage": STAGE,
        "final_collection_authorized": False,
        "run_id": args.run_id,
        "plan_sha256": _sha256(args.plan),
        "integrity": integrity,
        "targets_full_width": targets,
        "projections": projections,
        "selected_final_seed_count": selected,
        "selection_status": "candidate-selected-requires-new-protocol" if selected else "no-candidate-selected",
        "note": "Effect means and directions are intentionally omitted from this planning report.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({
        "selected_final_seed_count": selected,
        "selection_status": report["selection_status"],
        "archives": integrity["archives"],
        "manifests": integrity["manifests"],
        "policy_results": integrity["policy_results"],
    }, indent=2))


if __name__ == "__main__":
    main()
