"""Assign mechanical anchors for R-instances from component positions.

Extracts verbatim substrings from both arms' A0 source for R1-R4 instances.
The demark transform preserves inner content, so the same text appears in both arms.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_anchor_explicit(
    text: str,
    line_num: int,
    demark_rule: str,
) -> str:
    """Extract a short anchor from the explicit source at the given line."""
    lines = text.split("\n")
    line_idx = line_num - 1
    if line_idx < 0 or line_idx >= len(lines):
        return ""
    line = lines[line_idx].strip()
    anchor = ""

    if demark_rule == "D1":
        for i in range(line_idx, min(line_idx + 5, len(lines))):
            l = lines[i].strip()
            m = re.match(r"^\d+\.\s+(.+)", l)
            if m:
                anchor = m.group(1).strip()
                break
        if not anchor:
            anchor = line

    elif demark_rule == "D2":
        for i in range(line_idx, min(line_idx + 10, len(lines))):
            l = lines[i].strip()
            if l.startswith("<") or l.startswith("```") or not l:
                continue
            anchor = l[:60].strip()
            break
        if not anchor:
            anchor = line

    elif demark_rule == "D3":
        for i in range(line_idx, min(line_idx + 5, len(lines))):
            l = lines[i].strip()
            # Skip directive markers, closing tags, and code fences
            if (
                l.startswith(":::")
                or l.startswith("</")
                or l.startswith("```")
                or not l
            ):
                continue
            anchor = l[:60].strip()
            break
        if not anchor:
            anchor = line

    elif demark_rule == "D4":
        anchor = line

    elif demark_rule == "D7":
        for i in range(line_idx, min(line_idx + 4, len(lines))):
            l = lines[i].strip()
            if l.startswith("|") and not re.match(r"^\|[\s:]-", l):
                cells = [c.strip() for c in l.split("|") if c.strip()]
                if cells:
                    anchor = cells[0]
                    break
        if not anchor:
            anchor = "(table)"

    elif demark_rule == "D8":
        anchor = re.sub(r"^#+\s+", "", line)
    else:
        anchor = line

    anchor = re.sub(r"```", "", anchor)[:60].strip()
    return anchor


def _find_in_implicit(
    explicit_anchor: str, implicit_text: str, demark_rule: str = ""
) -> str:
    """Find anchor text in implicit source.

    For D8: heading text was replaced by template lead-in in the implicit arm.
    """
    if not explicit_anchor:
        return ""

    if demark_rule == "D8":
        norm_implicit = _normalize(implicit_text)
        for leadin in [
            "Before you begin, you need the following:",
            "Before you begin, you need the following",
        ]:
            idx = norm_implicit.lower().find(leadin.lower())
            if idx >= 0:
                return norm_implicit[idx : idx + len(leadin)]

    norm_anchor = _normalize(explicit_anchor)
    norm_implicit = _normalize(implicit_text)
    idx = norm_implicit.lower().find(norm_anchor.lower())
    if idx >= 0:
        return norm_implicit[idx : idx + len(norm_anchor)]
    short = norm_anchor[:30]
    idx = norm_implicit.lower().find(short.lower())
    if idx >= 0:
        return norm_implicit[idx : idx + len(short)]
    return ""


def assign_anchors(
    instances_csv: Path,
    specimens_csv: Path,
    explicit_dir: Path,
    implicit_dir: Path,
    output: Path | None = None,
) -> int:
    """Assign mechanical anchors for R-instances. Returns count."""
    if output is None:
        output = instances_csv

    with instances_csv.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    explicit_sources: dict[str, str] = {}
    implicit_sources: dict[str, str] = {}
    with specimens_csv.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sid = row["specimen_id"]
            ep = explicit_dir / row["source_path"]
            ip = implicit_dir / row["source_path"]
            if ep.exists():
                explicit_sources[sid] = ep.read_text(encoding="utf-8")
            if ip.exists():
                implicit_sources[sid] = ip.read_text(encoding="utf-8")

    anchored = 0
    for row in rows:
        rt = row["relation_type"]
        dr = row["demark_rule"]
        notes = row.get("notes", "")
        sid = row["specimen_id"]
        if not rt.startswith("R"):
            continue
        if (
            row.get("anchor_explicit", "").strip()
            and row.get("anchor_implicit", "").strip()
        ):
            continue
        line_m = re.search(r"at line (\d+)", notes)
        if not line_m:
            continue
        line_num = int(line_m.group(1))
        explicit_text = explicit_sources.get(sid)
        implicit_text = implicit_sources.get(sid)
        if not explicit_text or not implicit_text:
            continue
        anchor_explicit = _extract_anchor_explicit(explicit_text, line_num, dr)
        if not anchor_explicit:
            continue
        anchor_implicit = _find_in_implicit(anchor_explicit, implicit_text, dr)
        if not anchor_implicit:
            anchor_implicit = anchor_explicit
        row["anchor_explicit"] = anchor_explicit
        row["anchor_implicit"] = anchor_implicit
        anchored += 1

    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return anchored


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--instances", type=Path, default=Path("instruments/instances.csv")
    )
    parser.add_argument("--specimens", type=Path, default=Path("corpus/specimens.csv"))
    parser.add_argument("--explicit-dir", type=Path, default=Path("corpus/explicit"))
    parser.add_argument("--implicit-dir", type=Path, default=Path("corpus/implicit"))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    n = assign_anchors(
        args.instances,
        args.specimens,
        args.explicit_dir,
        args.implicit_dir,
        args.output,
    )
    print(f"Assigned anchors for {n} R-instances")


if __name__ == "__main__":
    main()
