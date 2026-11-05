"""Verify and analyze the authorized clustered-loss final campaign."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import re
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple


WORKLOADS = (
    "mutable-product-v1",
    "react-admin-dashboard-v1",
    "svelte-realworld-feed-v1",
)
REGIMES = ("balanced", "read-heavy", "write-intensive")
TRANSPORTS = ("redis-pubsub", "redis-streams")
PROFILES = ("dispersed-10", "single-burst-10")
ALL_PROFILES = ("no-fault", "dispersed-10", "single-burst-10", "repeated-bursts-10")
POLICIES = ("event-invalidate-with-repair", "always-invalidate")
PROTOCOL = "clustered-loss-protocol-v0.1"
FINAL_PROTOCOL_ID = "clustered-loss-final-protocol-v1"
STAGE = "extension-final"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_protocol(path: Path) -> Mapping[str, Any]:
    protocol = json.loads(path.read_text(encoding="utf-8"))
    if protocol.get("schema_version") != 1:
        raise ValueError("unsupported final-protocol schema")
    if protocol.get("protocol_id") != FINAL_PROTOCOL_ID:
        raise ValueError("unexpected final protocol ID")
    if protocol.get("protocol") != PROTOCOL:
        raise ValueError("unexpected clustered-loss protocol")
    if protocol.get("status") != "authorized-prospective":
        raise ValueError("final protocol is not prospectively authorized")
    if protocol.get("collection_authorized") is not True:
        raise ValueError("final collection is not authorized")
    if protocol.get("independent_unit") != "trace_seed":
        raise ValueError("final protocol changed the independent unit")
    if protocol.get("final_seed_count") != 84:
        raise ValueError("final protocol changed the authorized sample size")
    if protocol.get("interim_analysis") is not False:
        raise ValueError("final protocol permits interim analysis")
    if protocol.get("early_stopping") is not False:
        raise ValueError("final protocol permits early stopping")
    return protocol


def _load_run_map(path: Path) -> Mapping[int, str]:
    source = json.loads(path.read_text(encoding="utf-8"))
    result = {int(key): str(value) for key, value in source.items()}
    if set(result) != set(range(1, 7)):
        raise ValueError("run map must name exactly shards 1 through 6")
    if len(set(result.values())) != 6 or any(not value.isdigit() for value in result.values()):
        raise ValueError("run map must contain six unique numeric workflow run IDs")
    return result


def _artifact_name_pattern() -> re.Pattern[str]:
    return re.compile(
        r"^clustered-loss-final-s([1-6])-"
        r"(mutable-product-v1|react-admin-dashboard-v1|svelte-realworld-feed-v1)-"
        r"(balanced|read-heavy|write-intensive)-"
        r"(redis-pubsub|redis-streams)-(22[0-9]{2})-([0-9]+)\.zip$"
    )


def _expected_shard_by_seed(protocol: Mapping[str, Any]) -> Mapping[int, int]:
    result: Dict[int, int] = {}
    for shard in protocol["collection_shards"]:
        for seed in range(shard["seed_start"], shard["seed_start"] + shard["seed_count"]):
            if seed in result:
                raise ValueError("final protocol assigns a seed to multiple shards")
            result[seed] = shard["shard"]
    expected = set(
        range(protocol["final_seed_start"], protocol["final_seed_stop_exclusive"])
    )
    if set(result) != expected:
        raise ValueError("final protocol shard coverage is incomplete")
    return result


def _load_archive_inventories(
    archive_root: Path,
    run_map: Mapping[int, str],
) -> Mapping[str, str]:
    records: Dict[str, str] = {}
    for shard in range(1, 7):
        path = archive_root / f"shard-{shard}" / "archive_inventory.json"
        if not path.is_file():
            raise ValueError(f"missing archive inventory for shard {shard}")
        inventory = json.loads(path.read_text(encoding="utf-8"))
        if inventory.get("workflow_run_id") != int(run_map[shard]):
            raise ValueError(f"inventory run ID mismatch for shard {shard}")
        if inventory.get("artifact_count") != 252:
            raise ValueError(f"inventory artifact count mismatch for shard {shard}")
        expected_prefix = f"clustered-loss-final-s{shard}-"
        if inventory.get("artifact_prefix") != expected_prefix:
            raise ValueError(f"inventory artifact prefix mismatch for shard {shard}")
        for record in inventory.get("artifacts", []):
            name = record.get("name")
            digest = record.get("archive_sha256")
            github_digest = record.get("github_digest")
            if not isinstance(name, str) or not name.startswith(expected_prefix):
                raise ValueError(f"invalid inventory artifact name for shard {shard}")
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError(f"invalid inventory digest for {name}")
            if github_digest != f"sha256:{digest}":
                raise ValueError(f"GitHub digest mismatch recorded for {name}")
            if name in records:
                raise ValueError(f"duplicate inventory artifact name: {name}")
            records[name] = digest
    if len(records) != 1512:
        raise ValueError(f"expected 1512 inventory records, found {len(records)}")
    return records


def _read_results(
    archive_root: Path,
    protocol_path: Path,
    protocol: Mapping[str, Any],
    run_map: Mapping[int, str],
) -> Tuple[
    Mapping[Tuple[int, str, str, str, str, str], Mapping[str, Any]],
    Mapping[str, Any],
]:
    archives = sorted(archive_root.rglob("*.zip"))
    seeds = tuple(
        range(protocol["final_seed_start"], protocol["final_seed_stop_exclusive"])
    )
    expected_outer = set(itertools.product(WORKLOADS, REGIMES, TRANSPORTS, seeds))
    if len(archives) != len(expected_outer):
        raise ValueError(f"expected {len(expected_outer)} archives, found {len(archives)}")

    pattern = _artifact_name_pattern()
    inventory_digests = _load_archive_inventories(archive_root, run_map)
    shard_by_seed = _expected_shard_by_seed(protocol)
    protocol_sha256 = _sha256(protocol_path)
    outer = set()
    rows: Dict[Tuple[int, str, str, str, str, str], Mapping[str, Any]] = {}
    manifest_count = 0
    policy_result_count = 0
    archive_digests = {}
    source_commit_hashes = set()
    design_hashes = set()
    lock_hashes = set()
    for archive in archives:
        match = pattern.match(archive.name)
        if not match:
            raise ValueError(f"unexpected archive name: {archive.name}")
        shard_text, workload, regime, transport, seed_text, run_id = match.groups()
        shard = int(shard_text)
        seed = int(seed_text)
        if run_map[shard] != run_id:
            raise ValueError(f"workflow run mismatch in {archive.name}")
        if shard_by_seed.get(seed) != shard:
            raise ValueError(f"seed-to-shard mismatch in {archive.name}")
        identity = (workload, regime, transport, seed)
        if identity in outer:
            raise ValueError(f"duplicate archive identity: {identity}")
        outer.add(identity)
        archive_digest = _sha256(archive)
        if inventory_digests.get(archive.stem) != archive_digest:
            raise ValueError(f"archive differs from its verified inventory: {archive.name}")
        archive_digests[archive.name] = archive_digest
        with zipfile.ZipFile(archive) as zipped:
            failed_member = zipped.testzip()
            if failed_member:
                raise ValueError(f"CRC failure in {archive.name}: {failed_member}")
            members = [name for name in zipped.namelist() if not name.endswith("/")]
            if len(members) != 40:
                raise ValueError(f"expected 40 files in {archive.name}, found {len(members)}")
            base = f"{workload}-{regime}-{transport}-{seed}"
            for profile in ALL_PROFILES:
                prefix = f"{base}/{profile}/"
                manifest = json.loads(zipped.read(prefix + "manifest.json"))
                manifest_count += 1
                expected_block = {
                    "stage": STAGE,
                    "workload": workload,
                    "regime": regime,
                    "transport": transport,
                    "trace_seed": seed,
                    "fault_profile": profile,
                }
                if manifest.get("block_identity") != expected_block:
                    raise ValueError(f"block identity mismatch in {archive.name}/{profile}")
                if not manifest.get("passed"):
                    raise ValueError(f"failed manifest in {archive.name}/{profile}")
                if manifest.get("protocol") != PROTOCOL or manifest.get("stage") != STAGE:
                    raise ValueError(f"protocol or stage mismatch in {archive.name}/{profile}")
                if manifest.get("final_protocol_id") != FINAL_PROTOCOL_ID:
                    raise ValueError(f"final protocol ID mismatch in {archive.name}/{profile}")
                if manifest.get("final_protocol_sha256") != protocol_sha256:
                    raise ValueError(f"final protocol hash mismatch in {archive.name}/{profile}")
                if manifest.get("confirmatory_final_test") is not True:
                    raise ValueError("final manifest lacks the confirmatory flag")
                if manifest.get("final_extension_collection") is not True:
                    raise ValueError("final manifest lacks the collection flag")
                source_commit = manifest.get("source_commit")
                if not isinstance(source_commit, str) or not re.fullmatch(
                    r"[0-9a-f]{40}", source_commit
                ):
                    raise ValueError("final manifest lacks a valid source commit")
                source_commit_hashes.add(source_commit)
                design_hashes.add(manifest.get("clustered_loss_final_design_sha256"))
                lock_hashes.add(
                    json.dumps(manifest.get("parameter_lock_sha256"), sort_keys=True)
                )
                attempts = manifest.get("attempts", [])
                if len(attempts) != 4 or any(item.get("returncode") != 0 for item in attempts):
                    raise ValueError(f"incomplete policy attempts in {archive.name}/{profile}")
                for attempt in attempts:
                    policy = attempt["policy"]
                    result = json.loads(zipped.read(prefix + attempt["artifact"]))
                    policy_result_count += 1
                    if result.get("protocol") != PROTOCOL or result.get("stage") != STAGE:
                        raise ValueError(f"result protocol or stage mismatch in {archive.name}")
                    if result.get("confirmatory_final_test") is not True:
                        raise ValueError("final result lacks the confirmatory flag")
                    if result.get("final_extension_collection") is not True:
                        raise ValueError("final result lacks the collection flag")
                    if result.get("source_commit") != source_commit:
                        raise ValueError("result source commit differs from its manifest")
                    summary = result["summary"]
                    if summary.get("policy") != policy:
                        raise ValueError(f"policy mismatch in {archive.name}/{profile}")
                    for digest_name in ("trace_sha256", "fault_sha256", "schedule_sha256"):
                        if summary.get(digest_name) != manifest.get(digest_name):
                            raise ValueError(
                                f"{digest_name} mismatch in {archive.name}/{profile}"
                            )
                    if profile in PROFILES and policy in POLICIES:
                        key = (seed, workload, regime, transport, profile, policy)
                        if key in rows:
                            raise ValueError(f"duplicate result identity: {key}")
                        rows[key] = summary

    if outer != expected_outer:
        raise ValueError("final archive factorial is incomplete")
    expected_rows = len(expected_outer) * len(PROFILES) * len(POLICIES)
    if len(rows) != expected_rows:
        raise ValueError(f"expected {expected_rows} analysis rows, found {len(rows)}")
    if len(design_hashes) != 1 or None in design_hashes:
        raise ValueError("final archives do not share one design hash")
    if len(lock_hashes) != 1:
        raise ValueError("final archives do not share one parameter-lock hash set")
    if len(source_commit_hashes) != 1:
        raise ValueError("final artifacts do not share one source commit")
    integrity = {
        "archives": len(archives),
        "manifests": manifest_count,
        "policy_results": policy_result_count,
        "analysis_rows": len(rows),
        "archive_sha256": archive_digests,
        "design_sha256": next(iter(design_hashes)),
        "parameter_lock_sha256": json.loads(next(iter(lock_hashes))),
        "source_commit": next(iter(source_commit_hashes)),
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
                            or int(summary["requests_until_observed_terminal_recovery"])
                            > recovery_horizon
                        ),
                    }
                freshness.append(
                    values["single-burst-10"]["freshness"]
                    - values["dispersed-10"]["freshness"]
                )
                persistence.append(
                    values["single-burst-10"]["persistence"]
                    - values["dispersed-10"]["persistence"]
                )
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


def _quantile(sorted_values: Sequence[float], probability: float) -> float:
    position = probability * (len(sorted_values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction


def _bootstrap_interval(
    values: Sequence[float],
    *,
    replicates: int,
    confidence: float,
    rng: random.Random,
) -> Mapping[str, Any]:
    n = len(values)
    draws = sorted(
        statistics.fmean(values[rng.randrange(n)] for _ in range(n))
        for _ in range(replicates)
    )
    tail = (1.0 - confidence) / 2.0
    lower = _quantile(draws, tail)
    upper = _quantile(draws, 1.0 - tail)
    return {
        "estimate": statistics.fmean(values),
        "interval_lower": lower,
        "interval_upper": upper,
        "interval_full_width": upper - lower,
        "trace_seeds": n,
        "positive_seed_estimates": sum(value > 0 for value in values),
        "zero_seed_estimates": sum(value == 0 for value in values),
        "negative_seed_estimates": sum(value < 0 for value in values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive_root", type=Path)
    parser.add_argument("--run-map", type=Path, required=True)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path("experiments/freshness/clustered_loss_final_protocol_v1.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    protocol = _load_protocol(args.protocol)
    run_map = _load_run_map(args.run_map)
    rows, integrity = _read_results(
        args.archive_root,
        args.protocol,
        protocol,
        run_map,
    )
    seeds = range(protocol["final_seed_start"], protocol["final_seed_stop_exclusive"])
    values = _seed_estimates(rows, seeds, protocol["recovery_horizon_requests"])
    rng = random.Random(protocol["bootstrap"]["seed"])
    estimates = {
        metric: _bootstrap_interval(
            metric_values,
            replicates=protocol["bootstrap"]["replicates"],
            confidence=protocol["confidence_level"],
            rng=rng,
        )
        for metric, metric_values in values.items()
    }
    targets = protocol["precision_targets_full_width"]
    for metric, estimate in estimates.items():
        estimate["precision_target_full_width"] = targets[metric]
        estimate["precision_target_met"] = (
            estimate["interval_full_width"] <= targets[metric]
        )
    report = {
        "analysis": "clustered-loss-final-v1",
        "protocol": PROTOCOL,
        "final_protocol_id": FINAL_PROTOCOL_ID,
        "stage": STAGE,
        "confirmatory_final_test": True,
        "final_extension_collection": True,
        "run_map": {str(key): value for key, value in sorted(run_map.items())},
        "protocol_sha256": _sha256(args.protocol),
        "integrity": integrity,
        "interval_policy": protocol["interval_policy"],
        "bootstrap": protocol["bootstrap"],
        "estimates": estimates,
        "all_precision_targets_met": all(
            estimate["precision_target_met"] for estimate in estimates.values()
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                "archives": integrity["archives"],
                "manifests": integrity["manifests"],
                "policy_results": integrity["policy_results"],
                "all_precision_targets_met": report["all_precision_targets_met"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
