"""Probe authoring surface (P6 task 2) — surfaces instances and host passages.

The phase reserves probe authoring to the human analyst; this script only
*surfaces* the per-instance material probes are written against — instance id,
relation type, demark rule, anchors, and both host passages — so the analyst
authors without hunting through raw CSV. It never drafts probe text.

Output is a Markdown file under ``build/`` (gitignored); one section per
specimen, one block per instance.

Usage:
    uv run python -m docs_transduction_study.probe_sheet [--out PATH]
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTANCES_CSV = REPO_ROOT / "instruments" / "instances.csv"
SPECIMENS_CSV = REPO_ROOT / "corpus" / "specimens.csv"
DEFAULT_OUT = REPO_ROOT / "build" / "probe-authoring-sheet.md"


def build_sheet(
    instances_path: Path = INSTANCES_CSV,
    specimens_path: Path = SPECIMENS_CSV,
    out_path: Path = DEFAULT_OUT,
) -> Path:
    with instances_path.open("r", encoding="utf-8") as f:
        instances = list(csv.DictReader(f))
    with specimens_path.open("r", encoding="utf-8") as f:
        specimens = {row["specimen_id"]: row for row in csv.DictReader(f)}

    # Group by specimen, preserving instance order.
    by_specimen: dict[str, list[dict[str, str]]] = {}
    for row in instances:
        by_specimen.setdefault(row["specimen_id"], []).append(row)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# Probe authoring sheet (generated — do not edit)",
        "",
        (
            "One block per relation instance. All text below is source material; "
            "probe question, correct answer, and foils are authored by the analyst."
        ),
        "",
    ]
    for sid in sorted(by_specimen):
        spec = specimens.get(sid, {})
        lines.append(f"## {sid} — {spec.get('source_path', '?')}")
        lines.append("")
        lines.append(
            f"Diátaxis type: `{spec.get('diataxis_type', '?')}` · "
            f"last_major_change_version: `{spec.get('last_major_change_version', '?')}`"
        )
        lines.append("")
        for row in by_specimen[sid]:
            lines.append(f"### {row['instance_id']}")
            lines.append("")
            lines.append(
                f"- relation_type: `{row.get('relation_type', '')}` · "
                f"demark_rule: `{row.get('demark_rule', '') or '(observed)'}`"
            )
            anchor_ex = row.get("anchor_explicit", "").strip()
            anchor_im = row.get("anchor_implicit", "").strip()
            lines.append("- anchor (explicit):")
            lines.append(f"  ```{anchor_ex}```")
            lines.append("- anchor (implicit):")
            lines.append(f"  ```{anchor_im}```")
            lines.append("")
            lines.append("Host passage (explicit):")
            lines.append("")
            lines.append(f"> {row.get('host_passage_explicit', '').strip()}")
            lines.append("")
            lines.append("Host passage (implicit):")
            lines.append("")
            lines.append(f"> {row.get('host_passage_implicit', '').strip()}")
            notes = row.get("notes", "").strip()
            if notes:
                lines.append("")
                lines.append(f"Notes: {notes}")
            lines.append("")
            lines.append("---")
            lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out = build_sheet(out_path=args.out)
    print(f"Probe authoring sheet written: {out}")


if __name__ == "__main__":
    main()
