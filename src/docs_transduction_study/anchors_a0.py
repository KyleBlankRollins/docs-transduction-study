"""Anchors A0 — verify every retained instance resolves uniquely in both A0 arms.

For each instance not excluded at the gate, per arm: the host passage occurs
exactly once verbatim in that arm's A0 source; its projected text and its start
and end locators are unique in the projected page (``locators``); and the anchor
is markup-free, unique in the projected page, and occurs exactly once inside the
host. Gate-excluded instances are listed but not resolved.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

from docs_transduction_study import locators


def _normalize(text: str) -> str:
    """Collapse whitespace and fold typographic quotes and dashes (legacy spec)."""
    text = re.sub(r"\s+", " ", text)
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    return text.strip()


def resolve_anchor(anchor: str, a0_source: str) -> bool:
    """Legacy presence check (normalized substring); kept for compatibility."""
    if not anchor:
        return True
    return _normalize(anchor).lower() in _normalize(a0_source).lower()


def check_instance(anchor: str, host: str, source: str) -> list[str]:
    """Return resolution problems for one arm of one instance."""
    problems: list[str] = []
    if not anchor or not host:
        return ["missing anchor or host"]
    if source.count(host) != 1:
        return [f"host occurs {source.count(host)} times verbatim"]
    try:
        locators.locators(host, source)
    except ValueError as error:
        problems.append(str(error))
    projected = locators.project_mdx(source)
    if len(locators.find_all(anchor, projected)) != 1:
        problems.append("anchor is not unique in the projected page")
    if len(locators.find_all(anchor, host)) != 1:
        problems.append("anchor does not occur exactly once in the host")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--instances", type=Path, default=Path("instruments/instances.csv")
    )
    parser.add_argument(
        "--exclusions", type=Path, default=Path("instruments/gate_exclusions.csv")
    )
    parser.add_argument("--explicit-dir", type=Path, default=Path("corpus/explicit"))
    parser.add_argument("--implicit-dir", type=Path, default=Path("corpus/implicit"))
    parser.add_argument("--specimens", type=Path, default=Path("corpus/specimens.csv"))
    args = parser.parse_args()

    with args.specimens.open("r", encoding="utf-8") as f:
        spec_paths = {
            row["specimen_id"]: row["source_path"] for row in csv.DictReader(f)
        }
    with args.instances.open("r", encoding="utf-8") as f:
        instances = list(csv.DictReader(f))
    excluded: set[str] = set()
    if args.exclusions.exists():
        with args.exclusions.open("r", encoding="utf-8") as f:
            excluded = {row["instance_id"] for row in csv.DictReader(f)}

    failures: list[str] = []
    checked = 0
    for row in instances:
        if row["instance_id"] in excluded:
            continue
        source_path = spec_paths.get(row["specimen_id"])
        if not source_path:
            failures.append(f"{row['instance_id']}: unknown specimen")
            continue
        checked += 1
        for arm, directory in (
            ("explicit", args.explicit_dir),
            ("implicit", args.implicit_dir),
        ):
            source = (directory / source_path).read_text(encoding="utf-8")
            for problem in check_instance(
                row[f"anchor_{arm}"], row[f"host_passage_{arm}"], source
            ):
                failures.append(f"{row['instance_id']}/{arm}: {problem}")

    for failure in failures:
        print(f"  FAIL: {failure}", file=sys.stderr)
    if failures:
        print(f"\n{len(failures)} A0 resolution failure(s)", file=sys.stderr)
        sys.exit(1)
    print(
        f"All {checked} retained instance(s) resolve uniquely in both A0 arms "
        f"(host, locators, anchor); {len(excluded)} gate-excluded instance(s) skipped."
    )


if __name__ == "__main__":
    main()
