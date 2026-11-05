"""Build one authorized GitHub Actions matrix for clustered-loss final collection."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path


def build(protocol_path: Path, shard_number: int) -> dict:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("status") != "authorized-prospective":
        raise ValueError("final protocol is not prospectively authorized")
    if protocol.get("collection_authorized") is not True:
        raise ValueError("final collection is not authorized")
    shards = {item["shard"]: item for item in protocol["collection_shards"]}
    if shard_number not in shards:
        raise ValueError(f"unknown collection shard: {shard_number}")
    shard = shards[shard_number]
    seeds = range(shard["seed_start"], shard["seed_start"] + shard["seed_count"])
    include = [
        {
            "shard": shard_number,
            "workload": workload,
            "regime": regime,
            "transport": transport,
            "seed": seed,
        }
        for workload, regime, transport, seed in itertools.product(
            protocol["workloads"],
            protocol["regimes"],
            protocol["transports"],
            seeds,
        )
    ]
    if len(include) != protocol["jobs_per_shard"]:
        raise ValueError("generated matrix does not match the authorized shard size")
    identities = {
        (item["workload"], item["regime"], item["transport"], item["seed"])
        for item in include
    }
    if len(identities) != len(include):
        raise ValueError("generated matrix contains duplicate identities")
    return {"include": include}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard", type=int, required=True)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path(
            "experiments/freshness/clustered_loss_final_protocol_v1.json"
        ),
    )
    args = parser.parse_args()
    print(json.dumps(build(args.protocol, args.shard), separators=(",", ":")))


if __name__ == "__main__":
    main()
