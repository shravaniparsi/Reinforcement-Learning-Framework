"""Download one completed clustered-loss final shard without extraction."""

from __future__ import annotations

import argparse
from pathlib import Path

from .artifact_archives import download_run_archives


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo")
    parser.add_argument("run_id", type=int)
    parser.add_argument("shard", type=int, choices=range(1, 7))
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    download_run_archives(
        args.repo,
        args.run_id,
        args.output_root / f"shard-{args.shard}",
        artifact_prefix=f"clustered-loss-final-s{args.shard}-",
        expected_artifacts=252,
        expected_files_per_artifact=40,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()
