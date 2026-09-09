"""Probe linter — enforce the probe authoring rules by code (P6, W5).

Checks enforced:

1. **Exactly one probe per instance** — a full join against
   ``instances.csv``: every instance has exactly one probe row **or** exactly
   one gate-exclusion row, never both and never two of the same. Equivalently,
   ``len(instances) == len(probes) + len(exclusions)`` with disjoint, covering
   ``instance_id`` sets.
2. **No probe string verbatim in either arm's A0 source** — the
   distinctive-string rule. None of the probe's free-text fields
   (``question``, ``correct_answer``, ``foil_1``, ``foil_2``,
   ``superseded_answer``) may appear in the specimen's explicit *or* implicit
   A0 source, whether as an exact substring or up to whitespace collapsing
   (a phrase spanning a line break in MDX is still a quote). Fields shorter
   than 4 non-whitespace characters are below the "distinctive string"
   threshold and are not checked.
3. **Foil cap** — at most two foils (``foil_1`` required, ``foil_2``
   optional), per design v0.5.
4. **Foils are relations, not paraphrases of absence** — a fixed absence
   wordlist catches "the text does not say"-style foils. The linter also
   rejects a foil that duplicates the correct answer or the other foil.
5. **Version-change probes** — ``version_change=true`` rows must have
   non-empty ``superseded_answer`` **and** ``superseded_source``; a
   ``version_change=false`` row must not carry superseded content.

Schema checks: both CSVs must carry the §3 contract headers, and
``instance_id`` must be unique in ``instances.csv``.

Exit code is 0 only when every check passes; the gate's equality is included
(probe count == instance count minus exclusion count).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTANCES_CSV = REPO_ROOT / "instruments" / "instances.csv"
PROBES_CSV = REPO_ROOT / "instruments" / "probes.csv"
GATE_EXCLUSIONS_CSV = REPO_ROOT / "instruments" / "gate_exclusions.csv"
SPECIMENS_CSV = REPO_ROOT / "corpus" / "specimens.csv"
EXPLICIT_DIR = REPO_ROOT / "corpus" / "explicit"
IMPLICIT_DIR = REPO_ROOT / "corpus" / "implicit"

PROBES_HEADERS = [
    "probe_id",
    "instance_id",
    "question",
    "correct_answer",
    "foil_1",
    "foil_2",
    "version_change",
    "superseded_answer",
    "superseded_source",
]

EXCLUSIONS_HEADERS = ["instance_id", "reason", "failed_arm", "date"]

# Free-text probe fields subject to the distinctive-string rule.
PROBE_TEXT_FIELDS = [
    "question",
    "correct_answer",
    "foil_1",
    "foil_2",
    "superseded_answer",
]

# Minimum "distinctive string" size: shorter collapsed strings (e.g. a bare
# article or a two-letter word) match trivially and are not checkable.
MIN_DISTINCTIVE_LEN = 4

# Lowercased absence paraphrases a foil must never be. "The text does not say"
# is appended at presentation time and is never stored; a stored foil that
# rephrases it defeats the rubric's scoring design.
_ABSENCE_PHRASES: tuple[str, ...] = (
    "the text does not say",
    "the document does not say",
    "the docs do not say",
    "text does not say",
    "document does not say",
    "does not say",
    "doesn't say",
    "does not state",
    "doesn't state",
    "not stated",
    "never stated",
    "is not stated",
    "not mentioned",
    "never mentioned",
    "is not mentioned",
    "does not mention",
    "doesn't mention",
    "no mention",
    "not mention",
    "no mention of",
    "not mentioned anywhere",
    "not in the text",
    "not in the document",
    "text says nothing",
    "document says nothing",
    "says nothing about",
    "nothing about it",
    "nothing about this",
    "is silent",
    "is silent about",
    "silent about",
    "makes no mention",
    "no reference",
    "no reference to",
    "no information",
    "not enough information",
    "cannot be determined",
    "can't be determined",
    "cannot be told",
    "not determinable",
    "not present",
    "isn't present",
    "is absent",
    "absent from",
    "nowhere",
    "not covered",
    "does not cover",
    "doesn't cover",
    "not included",
    "omitted",
    "not stated anywhere",
    "not addressed",
    "does not address",
    "doesn't address",
    "not revealed",
    "not given",
    "not provided",
    "not told",
    "not indicated",
    "no indication",
)


def _collapse_whitespace(text: str) -> str:
    """Collapse all whitespace runs to single spaces and strip."""
    return re.sub(r"\s+", " ", text).strip()


def _parse_bool(value: str | None) -> bool | None:
    """Parse a version_change cell. Returns True/False, None if malformed."""
    if value is None:
        return False
    v = value.strip().lower()
    if v in ("", "0", "false", "no", "n"):
        return False
    if v in ("1", "true", "yes", "y"):
        return True
    return None


def _is_absence_like(foil: str) -> bool:
    """True if a foil paraphrases absence rather than naming a wrong relation."""
    lowered = _collapse_whitespace(foil).lower()
    for phrase in _ABSENCE_PHRASES:
        if phrase in lowered:
            return True
    return False


class LinterReport:
    """Collects errors so the final summary is readable."""

    def __init__(self) -> None:
        self.errors: list[str] = []

    def add(self, message: str) -> None:
        self.errors.append(message)

    @property
    def count(self) -> int:
        return len(self.errors)


def _read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    """Read a UTF-8 CSV, returning (rows, errors). Empty file is an error."""
    errors: list[str] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return [], [f"{path}: empty file (no header row)"]
        rows = [dict(r) for r in reader]
    return rows, errors


def _check_schema(
    report: LinterReport,
    rows: list[dict[str, str]],
    required_headers: list[str],
    label: str,
) -> None:
    if not rows:
        return
    missing = [h for h in required_headers if h not in rows[0]]
    if missing:
        report.add(f"SCHEMA: {label} missing required columns: {', '.join(missing)}")


def _load_source(
    report: LinterReport,
    specimens: dict[str, str],
    instance_rows: list[dict[str, str]],
    explicit_dir: Path,
    implicit_dir: Path,
) -> tuple[dict[str, str], dict[str, str]]:
    """Load each specimen's explicit and implicit A0 source as text.

    Returns (explicit_sources, implicit_sources) keyed by specimen_id.
    Missing files and unknown specimen_ids are reported as errors.
    """
    explicit_sources: dict[str, str] = {}
    implicit_sources: dict[str, str] = {}
    seen_specimens: set[str] = set()
    for row in instance_rows:
        sid = row["specimen_id"].strip()
        if sid in seen_specimens:
            continue
        seen_specimens.add(sid)
        source_path = specimens.get(sid)
        if source_path is None:
            report.add(f"A0: specimen_id '{sid}' not found in corpus/specimens.csv")
            continue
        for arm, direction, hold in (
            ("explicit", explicit_dir, explicit_sources),
            ("implicit", implicit_dir, implicit_sources),
        ):
            path = direction / source_path
            if not path.exists():
                report.add(f"A0: {arm} source missing for {sid}: {path}")
                continue
            hold[sid] = path.read_text(encoding="utf-8")
    return explicit_sources, implicit_sources


def _check_distinctive_strings(
    report: LinterReport,
    probe_row: dict[str, str],
    explicit_sources: dict[str, str],
    implicit_sources: dict[str, str],
) -> None:
    """No probe string appears verbatim in either arm's A0 source."""
    sid = probe_row.get("_specimen_id", "")
    for field in PROBE_TEXT_FIELDS:
        value = probe_row.get(field, "").strip()
        if not value:
            continue
        collapsed = _collapse_whitespace(value)
        if len(collapsed) < MIN_DISTINCTIVE_LEN:
            continue
        probe_id = probe_row.get("probe_id", "?")
        for arm, sources in (
            ("explicit", explicit_sources),
            ("implicit", implicit_sources),
        ):
            source = sources.get(sid, "")
            if not source:
                continue  # missing source already reported
            if collapsed in _collapse_whitespace(source) or collapsed in source:
                report.add(
                    f"VERBATIM: {probe_id} field '{field}' appears verbatim in "
                    f"{arm} A0 of {sid}"
                )
            elif value in _collapse_whitespace(source):
                report.add(
                    f"VERBATIM: {probe_id} field '{field}' appears verbatim in "
                    f"{arm} A0 of {sid} (line-wrapped in source)"
                )


def _check_foils(report: LinterReport, probe_row: dict[str, str]) -> None:
    """Foil cap and foil-vs-answer coherence."""
    probe_id = probe_row.get("probe_id", "?")
    correct = probe_row.get("correct_answer", "").strip()
    foil_1 = probe_row.get("foil_1", "").strip()
    foil_2 = probe_row.get("foil_2", "").strip()

    if not correct:
        report.add(f"FOIL: {probe_id} has no correct_answer")
    if not foil_1:
        report.add(
            f"FOIL: {probe_id} has no foil_1 (the design requires one or two foils)"
        )
    if (
        foil_1
        and foil_2
        and _collapse_whitespace(foil_1.lower()) == _collapse_whitespace(foil_2.lower())
    ):
        report.add(f"FOIL: {probe_id} foil_1 duplicates foil_2")
    if (
        correct
        and foil_1
        and _collapse_whitespace(foil_1.lower())
        == _collapse_whitespace(correct.lower())
    ):
        report.add(f"FOIL: {probe_id} foil_1 duplicates correct_answer")
    if (
        correct
        and foil_2
        and _collapse_whitespace(foil_2.lower())
        == _collapse_whitespace(correct.lower())
    ):
        report.add(f"FOIL: {probe_id} foil_2 duplicates correct_answer")
    for label, foil in (("foil_1", foil_1), ("foil_2", foil_2)):
        if not foil:
            continue
        collapsed = _collapse_whitespace(foil)
        if len(collapsed) < MIN_DISTINCTIVE_LEN:
            report.add(f"FOIL: {probe_id} {label} is too short to be a relation")
            continue
        if _is_absence_like(foil):
            report.add(f"FOIL: {probe_id} {label} paraphrases absence ('{foil}')")


def _check_version_change(report: LinterReport, probe_row: dict[str, str]) -> None:
    """version_change=true requires superseded_answer and superseded_source."""
    probe_id = probe_row.get("probe_id", "?")
    raw = probe_row.get("version_change", "")
    parsed = _parse_bool(raw)
    if parsed is None:
        report.add(f"VERSION: {probe_id} version_change must be a boolean, got '{raw}'")
        return
    superseded_answer = probe_row.get("superseded_answer", "").strip()
    superseded_source = probe_row.get("superseded_source", "").strip()
    if parsed:
        if not superseded_answer:
            report.add(
                f"VERSION: {probe_id} version_change=true but superseded_answer "
                "is empty"
            )
        if not superseded_source:
            report.add(
                f"VERSION: {probe_id} version_change=true but superseded_source "
                "is empty"
            )
    else:
        if superseded_answer or superseded_source:
            report.add(
                f"VERSION: {probe_id} version_change=false carries superseded "
                "content (incoherent row)"
            )


def _check_coverage(
    report: LinterReport,
    instances: list[dict[str, str]],
    probes: list[dict[str, str]],
    exclusions: list[dict[str, str]],
) -> None:
    """Exactly one probe per instance; full join, disjoint, covering."""
    instance_ids: set[str] = set()
    for row in instances:
        iid = row["instance_id"].strip()
        if iid in instance_ids:
            report.add(f"COVERAGE: duplicate instance_id '{iid}' in instances.csv")
        instance_ids.add(iid)

    probe_by_instance: dict[str, list[dict[str, str]]] = {}
    for row in probes:
        iid = row["instance_id"].strip()
        if not iid:
            report.add("COVERAGE: probe row with empty instance_id")
            continue
        probe_by_instance.setdefault(iid, []).append(row)
        if iid not in instance_ids:
            report.add(
                f"COVERAGE: probe {row.get('probe_id', '?')} references unknown "
                f"instance '{iid}'"
            )

    excl_by_instance: dict[str, list[dict[str, str]]] = {}
    for row in exclusions:
        iid = row["instance_id"].strip()
        if not iid:
            report.add("COVERAGE: exclusion row with empty instance_id")
            continue
        excl_by_instance.setdefault(iid, []).append(row)
        if iid not in instance_ids:
            report.add(f"COVERAGE: exclusion references unknown instance '{iid}'")
        if not row.get("reason", "").strip():
            report.add(f"EXCLUSION: {iid} has no reason")
        if not row.get("failed_arm", "").strip():
            report.add(f"EXCLUSION: {iid} has no failed_arm")
        if not row.get("date", "").strip():
            report.add(f"EXCLUSION: {iid} has no date")

    for iid in sorted(instance_ids):
        n_probe = len(probe_by_instance.get(iid, []))
        n_excl = len(excl_by_instance.get(iid, []))
        if n_probe == 1 and n_excl == 0:
            continue
        if n_probe == 0 and n_excl == 1:
            continue
        if n_probe > 1:
            report.add(f"COVERAGE: instance '{iid}' has {n_probe} probes (want 1)")
            continue
        if n_excl > 1:
            report.add(f"COVERAGE: instance '{iid}' has {n_excl} exclusions (want 1)")
            continue
        if n_probe == 1 and n_excl == 1:
            report.add(f"COVERAGE: instance '{iid}' has both a probe and an exclusion")
            continue
        report.add(f"COVERAGE: instance '{iid}' has no probe and no exclusion")

    if len(instances) != len(probes) + len(exclusions):
        report.add(
            f"COVERAGE: probe count ({len(probes)}) + exclusion count "
            f"({len(exclusions)}) != instance count ({len(instances)})"
        )


def _attach_specimen_ids(
    probes: list[dict[str, str]], instances: list[dict[str, str]]
) -> None:
    """Attach each probe's specimen_id as a hidden '_specimen_id' key."""
    spec_by_instance = {
        row["instance_id"].strip(): row.get("specimen_id", "").strip()
        for row in instances
    }
    for row in probes:
        row["_specimen_id"] = spec_by_instance.get(row["instance_id"].strip(), "")


def lint(
    instances_path: Path = INSTANCES_CSV,
    probes_path: Path = PROBES_CSV,
    exclusions_path: Path = GATE_EXCLUSIONS_CSV,
    specimens_path: Path = SPECIMENS_CSV,
    explicit_dir: Path = EXPLICIT_DIR,
    implicit_dir: Path = IMPLICIT_DIR,
) -> LinterReport:
    """Run every check and return a report. `report.count == 0` means pass."""
    report = LinterReport()

    instances, schema_errors = _read_csv(instances_path)
    probes, probe_schema_err = _read_csv(probes_path)
    exclusions, excl_schema_err = _read_csv(exclusions_path)
    for err in schema_errors + probe_schema_err + excl_schema_err:
        report.add(f"SCHEMA: {err}")

    if not instances:
        report.add("SCHEMA: instances.csv has no rows")
        return report

    _check_schema(report, probes, PROBES_HEADERS, "probes.csv")
    _check_schema(report, exclusions, EXCLUSIONS_HEADERS, "gate_exclusions.csv")

    _check_coverage(report, instances, probes, exclusions)

    _attach_specimen_ids(probes, instances)

    specimens: dict[str, str] = {}
    with specimens_path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            specimens[row["specimen_id"].strip()] = row["source_path"].strip()

    explicit_sources, implicit_sources = _load_source(
        report, specimens, instances, explicit_dir, implicit_dir
    )

    for probe_row in probes:
        _check_distinctive_strings(
            report, probe_row, explicit_sources, implicit_sources
        )
        _check_foils(report, probe_row)
        _check_version_change(report, probe_row)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instances", type=Path, default=INSTANCES_CSV)
    parser.add_argument("--probes", type=Path, default=PROBES_CSV)
    parser.add_argument("--gate-exclusions", type=Path, default=GATE_EXCLUSIONS_CSV)
    parser.add_argument("--specimens", type=Path, default=SPECIMENS_CSV)
    parser.add_argument("--explicit-dir", type=Path, default=EXPLICIT_DIR)
    parser.add_argument("--implicit-dir", type=Path, default=IMPLICIT_DIR)
    args = parser.parse_args()

    report = lint(
        args.instances,
        args.probes,
        args.gate_exclusions,
        args.specimens,
        args.explicit_dir,
        args.implicit_dir,
    )
    for err in report.errors:
        print(f"ERROR: {err}")
    if report.count:
        print(f"\n{report.count} error(s) — probes are not locked.")
        sys.exit(1)
    print("lint-probes: PASS — probes are locked.")


if __name__ == "__main__":
    main()
