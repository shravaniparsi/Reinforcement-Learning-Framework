"""Download GitHub Actions artifacts as verified, unexpanded ZIP archives."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path


def _gh(*arguments: str) -> bytes:
    process = subprocess.run(
        ('gh', *arguments),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode:
        raise RuntimeError(process.stderr.decode('utf-8', errors='replace'))
    return process.stdout


def valid_archive(path: Path, expected_files: int) -> bool:
    try:
        with zipfile.ZipFile(path) as archive:
            files = [name for name in archive.namelist() if not name.endswith('/')]
            return len(files) == expected_files and archive.testzip() is None
    except (OSError, zipfile.BadZipFile):
        return False


def _download(
    repo: str,
    artifact: dict,
    output: Path,
    expected_files: int,
) -> dict:
    destination = output / f"{artifact['name']}.zip"
    if not valid_archive(destination, expected_files):
        temporary = destination.with_suffix('.zip.part')
        payload = _gh(
            'api',
            f"repos/{repo}/actions/artifacts/{artifact['id']}/zip",
        )
        temporary.write_bytes(payload)
        if not valid_archive(temporary, expected_files):
            raise ValueError(f"invalid downloaded archive: {artifact['name']}")
        os.replace(temporary, destination)
    return {
        'artifact_id': artifact['id'],
        'name': artifact['name'],
        'github_size_in_bytes': artifact['size_in_bytes'],
        'archive_size_in_bytes': destination.stat().st_size,
        'archive_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
    }


def download_run_archives(
    repo: str,
    run_id: int,
    output: Path,
    *,
    artifact_prefix: str,
    expected_artifacts: int,
    expected_files_per_artifact: int,
    workers: int,
) -> None:
    pages = json.loads(_gh(
        'api',
        f'repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100',
        '--paginate',
        '--slurp',
    ))
    artifacts = [artifact for page in pages for artifact in page['artifacts']]
    suffix = f'-{run_id}'
    artifacts = sorted(
        (
            artifact for artifact in artifacts
            if artifact['name'].startswith(artifact_prefix)
            and artifact['name'].endswith(suffix)
            and not artifact['expired']
        ),
        key=lambda artifact: artifact['name'],
    )
    if len(artifacts) != expected_artifacts:
        raise ValueError(
            f'expected {expected_artifacts} live artifacts, found {len(artifacts)}'
        )
    output.mkdir(parents=True, exist_ok=True)
    records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _download, repo, artifact, output, expected_files_per_artifact,
            )
            for artifact in artifacts
        ]
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            records.append(future.result())
            if index % 25 == 0 or index == expected_artifacts:
                print(
                    f'downloaded and verified {index}/{expected_artifacts}',
                    flush=True,
                )
    inventory = {
        'schema_version': 1,
        'repository': repo,
        'workflow_run_id': run_id,
        'artifact_prefix': artifact_prefix,
        'expected_files_per_artifact': expected_files_per_artifact,
        'artifact_count': len(records),
        'artifacts': sorted(records, key=lambda record: record['name']),
    }
    inventory_path = output / 'archive_inventory.json'
    inventory_path.write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )
