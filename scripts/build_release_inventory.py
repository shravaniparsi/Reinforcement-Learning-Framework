"""Rebuild the final-study checksum inventory after intentional release edits."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "reproducibility" / "final-study"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    files = {
        str(path.relative_to(ROOT)): sha256(path)
        for path in sorted(ROOT.rglob("*"))
        if path.is_file()
        and path.name != "inventory.json"
        and "__pycache__" not in path.parts
        and ".venv" not in path.parts
    }
    output = {
        "status": "version 1.0.0 release candidate; public licenses pending author approval",
        "files": files,
    }
    (ROOT / "inventory.json").write_text(json.dumps(output, indent=2) + "\n")
    print(f"Wrote {len(files)} checksums to {ROOT / 'inventory.json'}")


if __name__ == "__main__":
    main()
