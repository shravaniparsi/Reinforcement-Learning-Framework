"""Download a completed variance-planning campaign without extraction."""

from __future__ import annotations

import argparse
from pathlib import Path

from .artifact_archives import download_run_archives


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('repo')
    parser.add_argument('run_id', type=int)
    parser.add_argument('output', type=Path)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    download_run_archives(
        args.repo,
        args.run_id,
        args.output,
        artifact_prefix='freshness-variance-',
        expected_artifacts=720,
        expected_files_per_artifact=18,
        workers=args.workers,
    )


if __name__ == '__main__':
    main()
