"""Anchors A0 — verify every anchor resolves in both arms' A0 source."""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


def _normalize(text: str) -> str:
    """Normalize text per the committed normalization spec:
    - Collapse whitespace (including newlines) to single spaces
    - Fold typographic quotes and dashes
    - Case-insensitive matching
    """
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    # Fold typographic quotes
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    # Fold typographic dashes
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    return text.strip()


def resolve_anchor(anchor: str, a0_source: str) -> bool:
    """Check if anchor (normalized) is present in A0 source (normalized)."""
    if not anchor:
        return True  # Empty anchor = not yet assigned = trivially passes
    norm_anchor = _normalize(anchor)
    norm_source = _normalize(a0_source)
    return norm_anchor.lower() in norm_source.lower()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instances", type=Path, default=Path("instruments/instances.csv"))
    parser.add_argument("--explicit-dir", type=Path, default=Path("corpus/explicit"))
    parser.add_argument("--implicit-dir", type=Path, default=Path("corpus/implicit"))
    parser.add_argument("--specimens", type=Path, default=Path("corpus/specimens.csv"))
    args = parser.parse_args()

    # Read specimen paths
    spec_paths: dict[str, str] = {}
    with args.specimens.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            spec_paths[row["specimen_id"]] = row["source_path"]

    # Read instances
    with args.instances.open("r", encoding="utf-8") as f:
        instances = list(csv.DictReader(f))

    failures: list[str] = []
    total_anchored = 0

    for row in instances:
        inst_id = row["instance_id"]
        sid = row["specimen_id"]
        source_path = spec_paths.get(sid)
        if not source_path:
            continue

        a_explicit = row.get("anchor_explicit", "").strip()
        a_implicit = row.get("anchor_implicit", "").strip()

        if not a_explicit and not a_implicit:
            continue  # Not yet assigned
        total_anchored += 1

        explicit_file = args.explicit_dir / source_path
        implicit_file = args.implicit_dir / source_path

        if a_explicit and explicit_file.exists():
            if not resolve_anchor(a_explicit, explicit_file.read_text(encoding="utf-8")):
                msg = f"{inst_id}: explicit anchor '{a_explicit}' not found in A0"
                failures.append(msg)
                print(f"  FAIL: {msg}", file=sys.stderr)

        if a_implicit and implicit_file.exists():
            if not resolve_anchor(a_implicit, implicit_file.read_text(encoding="utf-8")):
                msg = f"{inst_id}: implicit anchor '{a_implicit}' not found in A0"
                failures.append(msg)
                print(f"  FAIL: {msg}", file=sys.stderr)

    if failures:
        print(f"\n{len(failures)} anchor(s) failed to resolve", file=sys.stderr)
        sys.exit(1)

    print(f"All {total_anchored} anchor(s) resolved in both arms (A0).")
    print(f"{len(instances) - total_anchored} instance(s) have no anchor yet (waiting on human assignment).")


if __name__ == "__main__":
    main()