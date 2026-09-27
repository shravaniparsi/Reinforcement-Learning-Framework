"""Run identifiers and provenance shared by training and evaluation."""
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def episode_seed(config, episode):
    # Independent of strategy so comparisons share exogenous conditions.
    identity = [config.network_preset, config.server_preset,
                config.device_profile, config.seed, episode]
    return int.from_bytes(hashlib.sha256(json.dumps(identity).encode()).digest()[:8], 'big')


def run_directory(kind):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return str(ROOT / 'experiments' / 'runs' / kind / f'{stamp}-{uuid4().hex[:8]}')


def source_metadata():
    def git(*args):
        try:
            return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    packages = {}
    for name in ['numpy', 'gymnasium', 'torch', 'scipy', 'playwright']:
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {'git_commit': git('rev-parse', 'HEAD'),
            'git_status': git('status', '--porcelain'),
            'source_sha256': {str(p.relative_to(ROOT)): file_hash(p)
                              for p in sorted((ROOT / 'src/env').glob('*.py'))},
            'python': sys.version, 'platform': platform.platform(),
            'packages': packages}
