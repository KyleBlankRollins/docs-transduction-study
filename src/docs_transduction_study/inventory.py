"""
P4 — Relation inventory: R1-R4 candidate extraction and O1/O2 surfacing.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# ── Patterns for R1-R4 candidate extraction ──────────────────────────────

_STEPS_PATTERN = re.compile(r"<Steps\b", re.IGNORECASE)

_CUSTOM_TAB_WRAPPERS = (
    "PackageManagerTabs|UIFrameworkTabs|AstroVueTabs"
    "|StaticSsrTabs|JavascriptFlavorTabs|AstroJSXTabs"
)
_TABS_PATTERN = re.compile(rf"<(?:Tabs|{_CUSTOM_TAB_WRAPPERS})\b", re.IGNORECASE)

_ASIDE_DIRECTIVE_PATTERN = re.compile(
    r"(?:^|\n)\s*:::(note|tip|caution|danger)\b",
    re.IGNORECASE | re.MULTILINE,
)
_ASIDE_COMPONENT_PATTERN = re.compile(r"<Aside\b", re.IGNORECASE)

_NORMATIVE_KEYWORDS = (
    "MUST NOT",
    "SHALL NOT",
    "SHOULD NOT",
    "NOT RECOMMENDED",
    "MUST",
    "SHALL",
    "REQUIRED",
    "SHOULD",
    "RECOMMENDED",
    "MAY",
    "OPTIONAL",
)
_KEYWORD_PATTERN = re.compile(
    r"(?<![A-Za-z])(?:" + "|".join(_NORMATIVE_KEYWORDS) + r")(?![A-Za-z])"
)

_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEPARATOR = re.compile(r"^\s*\|\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|\s*$")

_PREREQ_HEADING_PATTERN = re.compile(
    r"^(#{2,4})\s+.*\b(?:Prerequisites?|Requirements?|What You.?ll Need)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)

# ── O1/O2 patterns ───────────────────────────────────────────────────────

# O1: Referring expressions — "the <noun>", "your <noun>"
# "this <noun>" is rerouted to O2 (deixis); "the following <noun>" is cataphoric → O2.
_O1_PATTERN = re.compile(
    r"\b(?:the(?!\s+following)|your)\s+([A-Z][a-z]+(?:\s+[a-z]+)*)",
    re.IGNORECASE,
)
_O2_DEICTIC_NOUN = re.compile(
    r"\bthis\s+(step|guide|section|chapter|article|page|document|tutorial"
    r"|recipe|example|list|block|paragraph)\b",
    re.IGNORECASE,
)
_O2_LOCATIVE = re.compile(
    r"\b(?:as\s+)?(?:described|mentioned|stated|noted|explained|shown"
    r"|outlined|listed)(?:\s+above|\s+below|\s+previously| earlier)\b",
    re.IGNORECASE,
)
_O2_REFERENTIAL = re.compile(
    r"\b(?:see|refer\s+to|review)\s+(?:above|below|the\s+(?:previous|following"
    r"|next)\s+(?:section|step|chapter|page|example))\b",
    re.IGNORECASE,
)

# Rerouted from O1: "this + capitalized noun phrase" is cataphoric/demonstrative → O2
# No IGNORECASE: only match when the following word starts uppercase (proper noun
# or title-case noun phrase), avoiding sentence-initial pronoun uses.
_O2_THIS_PHRASE = re.compile(
    r"\bthis\s+([A-Z][a-z]+(?:\s+[a-z]+)*)",
)

# Rerouted from O1: "the following X" points forward → O2 (cataphoric deixis)
_O2_FOLLOWING = re.compile(
    r"\bthe\s+following\s+([a-z]+(?:\s+[a-z]+)*)",
)
# ── Instance data structure ──────────────────────────────────────────────


@dataclass
class Instance:
    """One relation instance per instruments/instances.csv schema."""

    instance_id: str
    specimen_id: str
    relation_type: str
    anchor_explicit: str = ""
    anchor_implicit: str = ""
    host_passage_explicit: str = ""
    host_passage_implicit: str = ""
    demark_rule: str = ""
    notes: str = ""

    def csv_row(self) -> dict[str, str]:
        return {
            "instance_id": self.instance_id,
            "specimen_id": self.specimen_id,
            "relation_type": self.relation_type,
            "anchor_explicit": self.anchor_explicit,
            "anchor_implicit": self.anchor_implicit,
            "host_passage_explicit": self.host_passage_explicit,
            "host_passage_implicit": self.host_passage_implicit,
            "demark_rule": self.demark_rule,
            "notes": self.notes,
        }


# ── Utility ──────────────────────────────────────────────────────────────


def _instance_id(specimen_id: str, relation_type: str, seq: int) -> str:
    return f"{specimen_id}-{relation_type}-{seq:03d}"


def _count_tables(text: str) -> int:
    """Count Markdown tables by header/separator pair."""
    lines = text.splitlines()
    return sum(
        _TABLE_ROW.match(lines[i]) is not None
        and i + 1 < len(lines)
        and _TABLE_SEPARATOR.match(lines[i + 1]) is not None
        for i in range(len(lines) - 1)
    )


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter and import statements from MDX."""
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
    text = re.sub(r"^import\s+.*?;?\n", "", text, flags=re.MULTILINE)
    return text


FIELD_NAMES = [
    "instance_id",
    "specimen_id",
    "relation_type",
    "anchor_explicit",
    "anchor_implicit",
    "host_passage_explicit",
    "host_passage_implicit",
    "demark_rule",
    "notes",
]

# ── R1-R4 candidate extraction ──────────────────────────────────────────


def extract_r_candidates(
    specimens_csv: Path,
    explicit_dir: Path,
) -> list[Instance]:
    """Extract R1-R4 candidates from the explicit arm."""
    instances: list[Instance] = []

    with specimens_csv.open("r", encoding="utf-8") as f:
        specimens = list(csv.DictReader(f))

    for spec in specimens:
        sid = spec["specimen_id"]
        source_path = spec["source_path"]
        source_file = explicit_dir / source_path

        if not source_file.exists():
            print(
                f"  WARNING: {source_file} not found, skipping {sid}", file=sys.stderr
            )
            continue

        text = source_file.read_text(encoding="utf-8")
        seq: dict[str, int] = {}

        def next_seq(rt: str, _seq: dict[str, int] = seq) -> int:
            _seq[rt] = _seq.get(rt, 0) + 1
            return _seq[rt]

        # R1 / D1: Steps
        for m in _STEPS_PATTERN.finditer(text):
            line = text[: m.start()].count("\n") + 1
            instances.append(
                Instance(
                    instance_id=_instance_id(sid, "R1", next_seq("R1")),
                    specimen_id=sid,
                    relation_type="R1",
                    demark_rule="D1",
                    notes=f"<Steps> block at line {line}",
                )
            )

        # R2 / D2: Tabs (raw + custom wrappers)
        for m in _TABS_PATTERN.finditer(text):
            line = text[: m.start()].count("\n") + 1
            tag_name = m.group(0)[1:]
            instances.append(
                Instance(
                    instance_id=_instance_id(sid, "R2", next_seq("R2")),
                    specimen_id=sid,
                    relation_type="R2",
                    demark_rule="D2",
                    notes=f"<{tag_name}> at line {line}",
                )
            )

        # R3 / D3: Asides (directives and component form)
        for m in _ASIDE_DIRECTIVE_PATTERN.finditer(text):
            line = text[: m.start()].count("\n") + 1
            aside_type = m.group(1).lower()
            instances.append(
                Instance(
                    instance_id=_instance_id(sid, "R3", next_seq("R3")),
                    specimen_id=sid,
                    relation_type="R3",
                    demark_rule="D3",
                    notes=f":::{aside_type} directive at line {line}",
                )
            )
        for m in _ASIDE_COMPONENT_PATTERN.finditer(text):
            line = text[: m.start()].count("\n") + 1
            instances.append(
                Instance(
                    instance_id=_instance_id(sid, "R3", next_seq("R3")),
                    specimen_id=sid,
                    relation_type="R3",
                    demark_rule="D3",
                    notes=f"<Aside> component at line {line}",
                )
            )
        # R3 / D4: Normative keywords
        for m in _KEYWORD_PATTERN.finditer(text):
            line = text[: m.start()].count("\n") + 1
            instances.append(
                Instance(
                    instance_id=_instance_id(sid, "R3", next_seq("R3")),
                    specimen_id=sid,
                    relation_type="R3",
                    demark_rule="D4",
                    notes=f"keyword '{m.group()}' at line {line}",
                )
            )

        # R4 / D7: Tables
        table_count = _count_tables(text)
        for ti in range(table_count):
            instances.append(
                Instance(
                    instance_id=_instance_id(sid, "R4", next_seq("R4")),
                    specimen_id=sid,
                    relation_type="R4",
                    demark_rule="D7",
                    notes=f"Table {ti + 1} of {table_count}",
                )
            )

        # R4 / D8: Prerequisite headings
        for m in _PREREQ_HEADING_PATTERN.finditer(text):
            line = text[: m.start()].count("\n") + 1
            heading_text = m.group(0).strip()
            instances.append(
                Instance(
                    instance_id=_instance_id(sid, "R4", next_seq("R4")),
                    specimen_id=sid,
                    relation_type="R4",
                    demark_rule="D8",
                    notes=f"Prerequisite heading '{heading_text}' at line {line}",
                )
            )

        r1 = seq.get("R1", 0)
        r2 = seq.get("R2", 0)
        r3 = seq.get("R3", 0)
        r4 = seq.get("R4", 0)
        print(f"  {sid}: R1={r1} R2={r2} R3={r3} R4={r4}")

    return instances


# ── O1/O2 candidate surfacing ────────────────────────────────────────────


def surface_o_candidates(
    specimens_csv: Path,
    explicit_dir: Path,
    implicit_dir: Path,
) -> list[Instance]:
    """Surface O1/O2 candidates from both arms' shared text."""
    instances: list[Instance] = []

    with specimens_csv.open("r", encoding="utf-8") as f:
        specimens = list(csv.DictReader(f))

    for spec in specimens:
        sid = spec["specimen_id"]
        source_path = spec["source_path"]

        explicit_file = explicit_dir / source_path
        if not explicit_file.exists():
            continue

        explicit_text = explicit_file.read_text(encoding="utf-8")
        body = re.sub(
            r"\A---\n.*?\n---\n|^import[^\n]*\n",
            lambda match: "".join(
                "\n" if char == "\n" else " " for char in match.group()
            ),
            explicit_text,
            flags=re.DOTALL | re.MULTILINE,
        )

        # O1: Referring expressions
        o1_matches: dict[tuple[int, int], str] = {}
        for m in _O1_PATTERN.finditer(body):
            expr = m.group(0).strip()
            if 2 <= len(expr.split()) <= 6:
                o1_matches[(m.start(), m.end())] = expr
        for (start, end), expr in sorted(o1_matches.items()):
            instances.append(
                Instance(
                    instance_id=f"{sid}-O1-at-{start:06d}",
                    specimen_id=sid,
                    relation_type="O1",
                    demark_rule="",
                    notes=f"Referring expression candidate: '{expr}'; A0 chars [{start},{end})",
                )
            )

        # O2: Deictic expressions
        o2_matches: dict[tuple[int, int], tuple[str, str]] = {}
        for m in _O2_DEICTIC_NOUN.finditer(body):
            o2_matches[(m.start(), m.end())] = (m.group(0).strip(), "deictic noun")
        for m in _O2_LOCATIVE.finditer(body):
            o2_matches[(m.start(), m.end())] = (m.group(0).strip(), "locative")
        for m in _O2_REFERENTIAL.finditer(body):
            o2_matches[(m.start(), m.end())] = (m.group(0).strip(), "referential")
        # Rerouted from O1: "this X" — demonstrative/cataphoric → O2
        for m in _O2_THIS_PHRASE.finditer(body):
            o2_matches[(m.start(), m.end())] = (
                m.group(0).strip(),
                "rerouted from O1 (this/demonstrative)",
            )
        # Rerouted from O1: "the following X" — cataphoric → O2
        for m in _O2_FOLLOWING.finditer(body):
            o2_matches[(m.start(), m.end())] = (
                m.group(0).strip(),
                "rerouted from O1 (cataphoric)",
            )
        for (start, end), (expr, source) in sorted(o2_matches.items()):
            instances.append(
                Instance(
                    instance_id=f"{sid}-O2-at-{start:06d}",
                    specimen_id=sid,
                    relation_type="O2",
                    demark_rule="",
                    notes=f"Deictic expression candidate ({source}): '{expr}'; A0 chars [{start},{end})",
                )
            )

        o1 = len(o1_matches)
        o2 = len(o2_matches)
        print(f"  {sid}: O1={o1} O2={o2}")

    return instances


# ── CSV I/O ──────────────────────────────────────────────────────────────


def write_instances_csv(instances: list[Instance], output: Path) -> None:
    """Write instances to CSV, preserving existing rows."""
    output.parent.mkdir(parents=True, exist_ok=True)

    existing: dict[str, Instance] = {}
    if output.exists():
        with output.open("r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                inst = Instance(
                    instance_id=row["instance_id"],
                    specimen_id=row["specimen_id"],
                    relation_type=row["relation_type"],
                    anchor_explicit=row.get("anchor_explicit", ""),
                    anchor_implicit=row.get("anchor_implicit", ""),
                    host_passage_explicit=row.get("host_passage_explicit", ""),
                    host_passage_implicit=row.get("host_passage_implicit", ""),
                    demark_rule=row.get("demark_rule", ""),
                    notes=row.get("notes", ""),
                )
                existing[inst.instance_id] = inst

    merged: dict[str, Instance] = dict(existing)
    if any("-at-" in instance.instance_id for instance in instances) and any(
        instance.relation_type in {"O1", "O2"} and "-at-" not in instance.instance_id
        for instance in existing.values()
    ):
        raise ValueError(
            "Cannot merge occurrence candidates into the legacy string-keyed inventory; "
            "write a separate review file and migrate classified occurrences explicitly"
        )
    for inst in instances:
        if inst.instance_id not in merged:
            merged[inst.instance_id] = inst

    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELD_NAMES, lineterminator="\n")
        writer.writeheader()
        for inst_id in sorted(merged.keys()):
            writer.writerow(merged[inst_id].csv_row())

    new_count = sum(1 for i in instances if i.instance_id not in existing)
    preserved_count = sum(1 for i in instances if i.instance_id in existing)
    total = len(merged)
    print(
        f"Wrote {total} instances to {output}"
        f" ({preserved_count} preserved from existing, {new_count} new)"
    )


# ── CLI ──────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--specimens",
        type=Path,
        default=Path("corpus/specimens.csv"),
    )
    parser.add_argument(
        "--explicit-dir",
        type=Path,
        default=Path("corpus/explicit"),
    )
    parser.add_argument(
        "--implicit-dir",
        type=Path,
        default=Path("corpus/implicit"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("instruments/instances.csv"),
    )
    parser.add_argument(
        "--r-only",
        action="store_true",
        help="Only extract R1-R4 candidates",
    )
    parser.add_argument(
        "--o-only",
        action="store_true",
        help="Only surface O1/O2 candidates",
    )
    args = parser.parse_args()

    r_candidates: list[Instance] = []
    o_candidates: list[Instance] = []

    if not args.o_only:
        print("Extracting R1-R4 candidates...")
        r_candidates = extract_r_candidates(args.specimens, args.explicit_dir)

    if not args.r_only:
        print("Surfacing O1/O2 candidates...")
        o_candidates = surface_o_candidates(
            args.specimens,
            args.explicit_dir,
            args.implicit_dir,
        )

    all_candidates = r_candidates + o_candidates
    write_instances_csv(all_candidates, args.output)

    type_counts: dict[str, int] = {}
    for inst in all_candidates:
        type_counts[inst.relation_type] = type_counts.get(inst.relation_type, 0) + 1
    print("\nCandidate summary:")
    for rt in ["R1", "R2", "R3", "R4", "O1", "O2"]:
        print(f"  {rt}: {type_counts.get(rt, 0)}")
    print(f"  Total: {len(all_candidates)}")


if __name__ == "__main__":
    main()
