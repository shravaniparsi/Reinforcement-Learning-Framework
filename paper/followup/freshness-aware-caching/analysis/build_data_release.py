"""Build deterministic core and raw-data assets for the freshness study."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable


VERSION = '1.0.0'
STEM = f'freshness-caching-study-v{VERSION}'


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def _copy(source: Path, target: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def _validate_analysis(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8'))
    expected = {
        'measurement_kind': 'confirmatory-final-analysis',
        'block_count': 4824,
        'full_trace_unit_count': 38592,
        'primary_estimate_count': 450,
        'p_values_reported': False,
        'simultaneous_familywise_coverage_claim': False,
    }
    for key, wanted in expected.items():
        if value.get(key) != wanted:
            raise ValueError(f'analysis {key} is {value.get(key)!r}, expected {wanted!r}')
    estimates = value.get('primary_estimates', [])
    if len(estimates) != 450 or {item.get('n') for item in estimates} != {67}:
        raise ValueError('analysis lacks 450 complete estimates with n=67')
    return value


def _validate_archives(root: Path) -> tuple[Path, list[Path]]:
    inventory_path = root / 'archive_inventory.json'
    inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
    if (
        inventory.get('workflow_run_id') != 41148624728
        or inventory.get('artifact_count') != 4824
        or inventory.get('expected_files_per_artifact') != 18
    ):
        raise ValueError('archive inventory does not describe the final campaign')
    records = inventory.get('artifacts', [])
    if len(records) != 4824:
        raise ValueError('archive inventory does not contain 4,824 records')
    archives = sorted(root.glob('*.zip'))
    if len(archives) != 4824:
        raise ValueError(f'found {len(archives)} ZIP archives, expected 4,824')
    by_stem = {path.stem: path for path in archives}
    secret_signatures = (
        b'github_pat_', b'ghp_', b'gho_', b'ghu_', b'ghs_', b'ghr_',
        b'akia', b'-----begin private key-----', b'client_secret',
        b'access_token', b'refresh_token',
    )
    for record in records:
        path = by_stem.get(record['name'])
        if path is None:
            raise ValueError(f'missing archive {record["name"]}')
        if path.stat().st_size != record['archive_size_in_bytes']:
            raise ValueError(f'archive size mismatch: {path.name}')
        if _sha256(path) != record['archive_sha256']:
            raise ValueError(f'archive checksum mismatch: {path.name}')
        with zipfile.ZipFile(path) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            if len(members) != inventory['expected_files_per_artifact']:
                raise ValueError(f'archive member-count mismatch: {path.name}')
            for member in members:
                parts = Path(member.filename).parts
                if member.filename.startswith('/') or '..' in parts:
                    raise ValueError(f'unsafe archive path: {path.name}:{member.filename}')
                payload = archive.read(member).lower()
                signature = next(
                    (item for item in secret_signatures if item in payload), None,
                )
                if signature is not None:
                    raise ValueError(
                        f'possible credential signature {signature!r} in '
                        f'{path.name}:{member.filename}'
                    )
    return inventory_path, archives


def _repository_commit(root: Path) -> str:
    return subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=root, text=True,
    ).strip()


def _manifest_rows(root: Path) -> Iterable[dict[str, object]]:
    for path in sorted(item for item in root.rglob('*') if item.is_file()):
        if path.name == 'MANIFEST.csv':
            continue
        yield {
            'path': path.relative_to(root).as_posix(),
            'size_bytes': path.stat().st_size,
            'sha256': _sha256(path),
        }


def _write_manifest(root: Path) -> None:
    with (root / 'MANIFEST.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=('path', 'size_bytes', 'sha256'))
        writer.writeheader()
        writer.writerows(_manifest_rows(root))


def _zip_core(root: Path, output: Path) -> None:
    timestamp = (2026, 10, 31, 0, 0, 0)
    with zipfile.ZipFile(
        output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9,
        allowZip64=True,
    ) as archive:
        for path in sorted(item for item in root.rglob('*') if item.is_file()):
            relative = f'{STEM}/{path.relative_to(root).as_posix()}'
            info = zipfile.ZipInfo(relative, date_time=timestamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)


def _tar_raw(archives: list[Path], output: Path) -> None:
    with tarfile.open(output, 'w', format=tarfile.PAX_FORMAT) as bundle:
        for path in archives:
            info = bundle.gettarinfo(str(path), arcname=f'{STEM}-raw/{path.name}')
            info.uid = 0
            info.gid = 0
            info.uname = ''
            info.gname = ''
            info.mtime = 0
            with path.open('rb') as stream:
                bundle.addfile(info, stream)


def _copy_core(
    staging: Path,
    repository: Path,
    analysis: Path,
    inventory: Path,
) -> None:
    paper = repository / 'paper/followup/freshness-aware-caching'
    files = {
        paper / 'release/README.md': staging / 'README.md',
        paper / 'release/DATA_DICTIONARY.md': staging / 'DATA_DICTIONARY.md',
        paper / 'release/zenodo_metadata.json': staging / 'zenodo_metadata.json',
        analysis: staging / 'processed/freshness-final-analysis.json',
        paper / 'output/results/primary_estimates.csv': staging / 'processed/primary_estimates.csv',
        paper / 'output/results/primary_contrast_summary.csv': staging / 'processed/primary_contrast_summary.csv',
        inventory: staging / 'raw/archive_inventory.json',
        paper / 'protocol/protocol_v0.5.md': staging / 'protocol/protocol_v0.5.md',
        repository / 'experiments/freshness/final_design_v1.json': staging / 'protocol/final_design_v1.json',
        repository / 'experiments/freshness/analyze_final_test.py': staging / 'code/analyze_final_test.py',
        paper / 'analysis/build_primary_results.py': staging / 'code/build_primary_results.py',
        paper / 'analysis/build_data_release.py': staging / 'code/build_data_release.py',
        repository / 'LICENSE': staging / 'licenses/MIT-LICENSE.txt',
        repository / 'DATA_LICENSE.md': staging / 'licenses/DATA_LICENSE.md',
    }
    for suffix in ('svg', 'pdf', 'png'):
        for number, name in (
            (1, 'repair_tradeoffs'), (2, 'write_reactive_tradeoffs'),
        ):
            source = paper / f'output/results/figure_{number}_{name}.{suffix}'
            files[source] = staging / f'figures/{source.name}'
    for source, target in files.items():
        _copy(source, target)
    _write(staging / 'repository_commit.txt', _repository_commit(repository) + '\n')
    _write_manifest(staging)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('analysis', type=Path)
    parser.add_argument('archives', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--repository', type=Path, default=Path.cwd())
    args = parser.parse_args()

    repository = args.repository.resolve()
    analysis = args.analysis.resolve()
    archives_root = args.archives.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    _validate_analysis(analysis)
    inventory, archives = _validate_archives(archives_root)

    with tempfile.TemporaryDirectory(prefix='freshness-release-') as temporary:
        staging = Path(temporary) / STEM
        staging.mkdir()
        _copy_core(staging, repository, analysis, inventory)
        core = output / f'{STEM}-core.zip'
        raw = output / f'{STEM}-raw-archives.tar'
        _zip_core(staging, core)
        _tar_raw(archives, raw)

    checksums = output / 'CHECKSUMS.sha256'
    _write(
        checksums,
        ''.join(f'{_sha256(path)}  {path.name}\n' for path in (core, raw)),
    )
    print(json.dumps({
        'version': VERSION,
        'repository_commit': _repository_commit(repository),
        'core': {'path': str(core), 'size_bytes': core.stat().st_size, 'sha256': _sha256(core)},
        'raw': {'path': str(raw), 'size_bytes': raw.stat().st_size, 'sha256': _sha256(raw)},
        'checksums': str(checksums),
        'raw_archive_count': len(archives),
    }, indent=2))


if __name__ == '__main__':
    main()
