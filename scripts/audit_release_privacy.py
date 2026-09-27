"""Scan the release package for common private paths, keys and GitHub tokens."""

import json
import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / "reproducibility" / "final-study"
PATTERNS = {
    "local_home": re.compile(r"/Users/[^/\s]+|/home/(?!runner(?:/|\b))[^/\s]+"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
}


def main() -> None:
    findings = []
    paths = [
        REPO / "README.md",
        REPO / "CITATION.cff",
        REPO / ".zenodo.json",
        REPO / "RELEASE_NOTES_v1.0.0.md",
        REPO / "LICENSE",
        REPO / "DATA_LICENSE.md",
        REPO / "LICENSE_SCOPE.md",
    ]
    paths.extend(path for path in PACKAGE.rglob("*") if path.is_file() and path.name not in {"inventory.json", "privacy-scan.json"})
    for path in paths:
        value = path.read_text(errors="replace")
        for label, pattern in PATTERNS.items():
            if pattern.search(value):
                findings.append({"file": str(path.relative_to(REPO)), "type": label})
    output = {
        "findings": findings,
        "scope": "Release metadata and every final-study package file; pattern scan is not a guarantee of absence of sensitive content",
        "excluded": "Full host manifests, shell logs, screenshots, traces and private-path report envelopes remain outside the release",
    }
    (PACKAGE / "privacy-scan.json").write_text(json.dumps(output, indent=2) + "\n")
    if findings:
        raise SystemExit(f"Privacy findings require review: {findings}")
    print(f"PASS: scanned {len(paths)} release files with no configured privacy-pattern matches")


if __name__ == "__main__":
    main()
