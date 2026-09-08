"""Anchors — resolve anchors in artifacts and emit A4 chunk assignment.

For every instance, locate its anchor in both arms' A3/A4 artifacts,
determine which A4 chunk contains the first character of its host passage,
and record spans_chunks (whether the host passage crosses a chunk boundary).

Usage:
    uv run python -m docs_transduction_study.anchors --instances CSV --a4-dir DIR
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTANCES_CSV = REPO_ROOT / "instruments" / "instances.csv"
SPECIMENS_CSV = REPO_ROOT / "corpus" / "specimens.csv"
ARTIFACTS_DIR = REPO_ROOT / "artifacts"


def _normalize(text: str) -> str:
    """Normalize per committed spec (matching anchors_a0.py):
    - Collapse whitespace to single spaces
    - Fold typographic quotes and dashes
    - Return case-folded text for matching
    """
    text = re.sub(r"\s+", " ", text)
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    return text.strip().lower()


def resolve_anchor_offset(anchor: str, text: str) -> int | None:
    """Return char offset of anchor in text, or None if not found.
    Normalizes both inputs per the committed spec. No fuzzy fallback.
    """
    norm_a = _normalize(anchor)
    norm_t = _normalize(text)
    idx = norm_t.find(norm_a)
    return idx if idx >= 0 else None


def find_chunk_for_offset(offset: int, chunks: list[dict]) -> dict | None:
    """Find chunk entry containing a given character offset."""
    for entry in chunks:
        start = entry["chunk_start"]
        end = start + entry["char_count"]
        if start <= offset < end:
            return entry
    return None


def compute_spans_chunks(hp: str, a3_text: str, chunks: list[dict]) -> bool:
    """Check if host passage crosses a chunk boundary in this arm.
    Uses inclusive-exclusive range: start <= offset < start + char_count.
    """
    norm_hp = _normalize(hp)
    norm_t = _normalize(a3_text)
    start = norm_t.find(norm_hp)
    if start < 0:
        return False
    # Last character position (inclusive) of the host passage
    last_char = start + len(norm_hp) - 1
    sc = find_chunk_for_offset(start, chunks)
    ec = find_chunk_for_offset(last_char, chunks)
    if sc is None or ec is None:
        return False
    return sc["chunk_index"] != ec["chunk_index"]


def assign_chunks(
    instances_csv: Path, a4_dir: Path, out_path: Path | None = None
) -> dict[str, Any]:
    """Assign A4 chunks to all instances and compute spans_chunks per arm."""
    if out_path is None:
        out_path = instances_csv

    with instances_csv.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    spec_paths: dict[str, str] = {}
    with SPECIMENS_CSV.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            spec_paths[row["specimen_id"]] = row["source_path"]

    fieldnames = list(rows[0].keys())
    for fn in ("chunk_explicit", "chunk_implicit", "spans_chunks"):
        if fn not in fieldnames:
            fieldnames.append(fn)

    total = 0
    resolved = 0

    for row in rows:
        sid = row["specimen_id"]
        source_path = spec_paths.get(sid)
        if not source_path:
            continue
        total += 1
        spans_any = False

        for arm, anchor_key, host_key in [
            ("explicit", "anchor_explicit", "host_passage_explicit"),
            ("implicit", "anchor_implicit", "host_passage_implicit"),
        ]:
            anchor = row.get(anchor_key, "").strip()
            host = row.get(host_key, "").strip()
            if not anchor:
                continue

            # Find A3 text for this specimen
            a3_dir = a4_dir.parent / "a3" / arm
            a3_txt = a3_dir / (
                source_path.replace(".mdx", ".txt").replace(".md", ".txt")
            )
            if not a3_txt.exists():
                a3_txt = a3_dir / source_path.replace(".mdx", ".md")
            if not a3_txt.exists():
                continue

            a3_text = a3_txt.read_text(encoding="utf-8")
            offset = resolve_anchor_offset(anchor, a3_text)
            if offset is None:
                continue

            # Load and filter chunk index to this page only (fix Finding 5)
            a4_arm_dir = a4_dir / arm
            cidx_path = a4_arm_dir / "_chunk_index.json"
            if not cidx_path.exists():
                continue

            all_chunks = json.loads(cidx_path.read_text(encoding="utf-8"))
            page_key = Path(a3_txt.name)
            page_chunks = [
                c for c in all_chunks if Path(c.get("page", "")).name == page_key.name
            ]
            if not page_chunks:
                continue

            chunk = find_chunk_for_offset(offset, page_chunks)
            if chunk:
                row[f"chunk_{arm}"] = chunk["chunk_path"]
                resolved += 1

                # spans_chunks: check host passage boundary crossing
                if host:
                    if compute_spans_chunks(host, a3_text, page_chunks):
                        spans_any = True

        row["spans_chunks"] = "True" if spans_any else "False"

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    return {"total": total, "resolved": resolved, "output": str(out_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instances", type=Path, default=INSTANCES_CSV)
    parser.add_argument("--a4-dir", type=Path, default=ARTIFACTS_DIR / "a4")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    results = assign_chunks(args.instances, args.a4_dir, args.output)
    print(
        f"Resolved anchors: {results['resolved']}/{results['total']}", file=sys.stderr
    )
    if results["resolved"] == 0 and results["total"] > 0:
        print("WARNING: No anchors resolved.", file=sys.stderr)


if __name__ == "__main__":
    main()
