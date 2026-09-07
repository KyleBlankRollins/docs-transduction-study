"""Merge human O1/O2 classification into instances.csv; assign O-anchors and host passages."""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _strip_frontmatter(text: str) -> str:
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
    text = re.sub(r"^import\s+.*?;?\n", "", text, flags=re.MULTILINE)
    return text


def _read_source(specimens_csv: Path, source_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not specimens_csv.exists():
        return result
    with specimens_csv.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sid = row["specimen_id"]
            fp = source_dir / row["source_path"]
            if fp.exists():
                result[sid] = fp.read_text(encoding="utf-8")
    return result


def _find_span(body: str, anchor: str, window: int = 300) -> str:
    """Return minimal span containing anchor in normalized body."""
    if not anchor:
        return ""
    norm_body = _normalize(body)
    norm_anchor = _normalize(anchor)
    for attempt in [norm_anchor, norm_anchor[:40], norm_anchor[:30]]:
        idx = norm_body.lower().find(attempt.lower())
        if idx >= 0:
            start = max(0, idx - window // 2)
            end = min(len(norm_body), idx + len(attempt) + window // 2)
            return norm_body[start:end].strip()
    return anchor


def _get_expression_from_notes(notes: str) -> str:
    m = re.search(r"'([^']+)'", notes)
    return m.group(1) if m else notes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instances", type=Path, default=Path("instruments/instances.csv"))
    parser.add_argument("--o1-review", type=Path, default=Path("instruments/o1_review.csv"))
    parser.add_argument("--o2-review", type=Path, default=Path("instruments/o2_review.csv"))
    parser.add_argument("--specimens", type=Path, default=Path("corpus/specimens.csv"))
    parser.add_argument("--explicit-dir", type=Path, default=Path("corpus/explicit"))
    parser.add_argument("--implicit-dir", type=Path, default=Path("corpus/implicit"))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    out = args.output or args.instances

    # Read review decisions: instance_id -> {accept, expression}
    decisions: dict[str, dict[str, str]] = {}
    for rp in [args.o1_review, args.o2_review]:
        if not rp.exists():
            continue
        with rp.open("r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                iid = row["instance_id"]
                decisions[iid] = {
                    "accept": row.get("accept", "").strip(),
                    "expression": row.get("expression", "").strip(),
                }

    # Read current instances
    with args.instances.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Pre-read specimen sources
    explicit_sources = _read_source(args.specimens, args.explicit_dir)
    implicit_sources = _read_source(args.specimens, args.implicit_dir)

    updated_rows: list[dict[str, str]] = []
    anchored = 0
    host_assigned = 0
    removed = 0

    for row in rows:
        iid = row["instance_id"]
        rt = row["relation_type"]
        decision = decisions.get(iid, {})

        # Remove rejected O-instances
        if rt.startswith("O") and decision.get("accept") == "NO":
            removed += 1
            continue

        # Keep — potentially update anchors and host passages
        if rt.startswith("O") and decision.get("accept") == "YES":
            expr = decision.get("expression", "")
            if expr:
                # Use expression as the anchor for both arms
                row["anchor_explicit"] = expr
                row["anchor_implicit"] = expr
                anchored += 1

        # Assign host passages (for all accepted instances)
        sid = row["specimen_id"]
        explicit_text = explicit_sources.get(sid)
        implicit_text = implicit_sources.get(sid)

        # Find anchor to search for in source
        a_explicit = row.get("anchor_explicit", "").strip()
        a_implicit = row.get("anchor_implicit", "").strip()

        if a_explicit and explicit_text:
            body = _strip_frontmatter(explicit_text)
            row["host_passage_explicit"] = _find_span(body, a_explicit)

        if a_implicit and implicit_text:
            body = _strip_frontmatter(implicit_text)
            row["host_passage_implicit"] = _find_span(body, a_implicit)

        if a_explicit or a_implicit:
            host_assigned += 1

        updated_rows.append(row)

    # Write output
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(updated_rows)

    print(f"Processed {len(rows)} instances")
    print(f"Removed (rejected O): {removed}")
    print(f"O-anchors assigned: {anchored}")
    print(f"Host passages assigned: {host_assigned}")
    print(f"Total remaining: {len(updated_rows)}")


if __name__ == "__main__":
    main()