"""Coding-order seed generation (P6, W5 / L2).

Generates the seed that fixes the coding order and the pass-2 sample at L2,
writes it to ``coding/seed``, and prints its SHA-256 checksum for
``runlog.md``. The checksum prefix convention matches the coding harness's
``_unlock_mapping`` (``hashlib.sha256(seed).hexdigest()[:16]``).

Refuses to run after the instrument is locked: a post-L2 seed change is an
amendment (``AMENDMENTS.md``), not a rerun.

Usage:
    uv run python -m docs_transduction_study.seed [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import secrets
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_FILE = REPO_ROOT / "coding" / "seed"
DESIGN_MD = REPO_ROOT / "DESIGN.md"
SEED_BYTES = 32  # 64 hex chars, matching the harness seed


def _generate_seed() -> str:
    return secrets.token_hex(SEED_BYTES)


def _checksum(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()[:16]


def _instrument_locked(path: Path = DESIGN_MD) -> bool:
    """True if DESIGN.md carries a locked instrument date in frontmatter."""
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("instrument_locked:"):
            value = line.split(":", 1)[1].strip().strip('"')
            return value.startswith("20")
    return False


def write_seed(
    path: Path = SEED_FILE, force: bool = False, design_md: Path = DESIGN_MD
) -> str:
    """Generate and write the seed. Returns the seed hex string."""
    if _instrument_locked(design_md):
        print(
            "ERROR: instrument is locked (DESIGN.md instrument_locked set); "
            "changing the coding-order seed after L2 is an amendment.",
            file=sys.stderr,
        )
        sys.exit(1)
    if path.exists() and not force:
        print(
            f"ERROR: {path} already exists; use --force to regenerate.",
            file=sys.stderr,
        )
        sys.exit(1)
    seed = _generate_seed()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(seed + "\n", encoding="utf-8")
    return seed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="regenerate and overwrite")
    args = parser.parse_args()
    seed = write_seed(force=args.force)
    print(f"coding/seed written: {SEED_FILE}")
    print(f"seed: {seed}")
    print(f"checksum (sha256[:16]): {_checksum(seed)}")


if __name__ == "__main__":
    main()
