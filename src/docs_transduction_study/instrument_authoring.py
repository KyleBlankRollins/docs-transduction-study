"""Compile reviewed per-specimen authoring files into the L2 instrument CSVs.

Source of truth: ``instruments/authoring/S??.toml`` (AI-assisted review under
amendment A3). Each file records a decision and reason for every O1/O2
occurrence candidate, and hosts, anchors, a probe, and per-arm gate evidence for
every retained instance. Compilation validates everything against both A0 arms
and then replaces ``instances.csv``, ``probes.csv``, ``gate_exclusions.csv``,
``occurrence_decisions.csv``, and ``gate_evidence.csv`` together, or none of them.

Authoring fields per instance (``[[candidate]]`` for O1/O2, ``[[relation]]`` for
R1-R4, keyed by ``id``):

* ``decision`` (candidates only): ``accept`` or ``reject``; ``reason`` always.
* ``host`` or ``host_from``/``host_to``: the explicit-arm host passage, matched
  whitespace-flexibly and stored as the exact A0 slice. Optional ``host_after``
  names a unique earlier marker when ``host_from`` text repeats. ``host_implicit*`` fields
  default to the explicit ones.
* ``anchor`` / ``anchor_implicit``: short markup-free text unique in the arm.
* ``question``, ``correct``, ``foil_1``, optional ``foil_2``.
* ``evidence`` / ``evidence_implicit``: verbatim A0 quotes supporting the
  correct answer in that arm, inside that arm's host (the both-arms gate).
* ``gate``: ``pass`` or ``fail``; failures need ``failed_arm`` and ``reason``.
* optional ``version_change``, ``superseded_answer``, ``superseded_source``.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docs_transduction_study import lint_probes, locators

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTRUMENTS = REPO_ROOT / "instruments"
AUTHORING = INSTRUMENTS / "authoring"
INSTANCE_FIELDS = [
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
DECISION_FIELDS = [
    "instance_id",
    "specimen_id",
    "relation_type",
    "expression",
    "explicit_start",
    "explicit_end",
    "implicit_start",
    "implicit_end",
    "occurrence_rank",
    "legacy_id",
    "legacy_accept",
    "legacy_reason",
    "decision",
    "reason",
    "reviewed",
]
EVIDENCE_FIELDS = ["instance_id", "arm", "answer", "evidence", "gate"]
ANCHOR_FORBIDDEN = set("`*_[]<>|#{}\\")
REJECTION_CODES = {
    "generic",
    "exophoric",
    "idiom",
    "not_referential",
    "fragment",
    "not_probeable",
    "wrong_relation",
    "code",
    "no_antecedent",
    "heading",
    "self_reference",
}


@dataclass
class Sources:
    explicit: str
    implicit: str

    def arm(self, name: str) -> str:
        return self.explicit if name == "explicit" else self.implicit


def _flexible(text: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in text.split()]
    if not parts:
        raise ValueError("Empty passage specification")
    return re.compile(r"\s+".join(parts))


def find_unique(needle: str, source: str, label: str) -> tuple[int, int]:
    matches = list(_flexible(needle).finditer(source))
    if len(matches) != 1:
        raise ValueError(
            f"{label} must occur exactly once in A0 (found {len(matches)}): {needle[:60]!r}"
        )
    return matches[0].span()


def arm_field(entry: dict[str, Any], name: str, arm: str) -> Any:
    """Implicit-arm fields default to their explicit counterparts."""
    if arm == "implicit" and f"{name}_implicit" in entry:
        return entry[f"{name}_implicit"]
    return entry.get(name)


def host_span(entry: dict[str, Any], source: str, arm: str) -> tuple[int, int]:
    implicit_range = arm == "implicit" and (
        "host_from_implicit" in entry or "host_to_implicit" in entry
    )
    whole = arm_field(entry, "host", arm)
    if isinstance(whole, str) and not implicit_range:
        return find_unique(whole, source, f"{arm} host")
    start_text, end_text = (
        arm_field(entry, "host_from", arm),
        arm_field(entry, "host_to", arm),
    )
    if not start_text or not end_text:
        raise ValueError(f"{arm} host needs host or host_from/host_to")
    after = arm_field(entry, "host_after", arm)
    if after:
        # Disambiguate repeated text: the first host_from after a unique marker.
        _, marker_end = find_unique(after, source, f"{arm} host_after")
        found = _flexible(start_text).search(source, marker_end)
        if found is None:
            raise ValueError(f"{arm} host_from not found after host_after")
        start, first_end = found.span()
    else:
        start, first_end = find_unique(start_text, source, f"{arm} host_from")
    tail = _flexible(end_text).search(source, start)
    if tail is None:
        raise ValueError(f"{arm} host_to not found after host_from: {end_text[:60]!r}")
    return start, max(tail.end(), first_end)


def check_anchor(anchor: str, source: str, span: tuple[int, int], arm: str) -> None:
    if not 6 <= len(anchor) <= 90 or ANCHOR_FORBIDDEN & set(anchor) or "\n" in anchor:
        raise ValueError(
            f"{arm} anchor must be 6-90 markup-free characters: {anchor!r}"
        )
    projected = locators.project_mdx(source)
    if len(locators.find_all(anchor, projected)) != 1:
        raise ValueError(f"{arm} anchor is not unique in projected A0: {anchor!r}")
    matches = [
        m
        for m in _flexible(anchor).finditer(source)
        if span[0] <= m.start() and m.end() <= span[1]
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{arm} anchor must occur once, verbatim, inside its host: {anchor!r}"
        )


def check_evidence(quote: str, source: str, span: tuple[int, int], arm: str) -> None:
    matches = [
        m
        for m in _flexible(quote).finditer(source)
        if span[0] <= m.start() and m.end() <= span[1]
    ]
    if not matches:
        raise ValueError(
            f"{arm} gate evidence is not a verbatim quote inside the host: {quote[:60]!r}"
        )


def compile_instance(
    entry: dict[str, Any], sources: Sources, occurrence: dict[str, str] | None
) -> dict[str, Any]:
    """Validate one retained instance; return per-arm hosts and anchors."""
    result: dict[str, Any] = {}
    for arm in ("explicit", "implicit"):
        source = sources.arm(arm)
        span = host_span(entry, source, arm)
        host = source[span[0] : span[1]]
        for fence in re.finditer(
            r"^[ \t]*(```|~~~)[^\n]*\n.*?^[ \t]*\1", source, re.DOTALL | re.MULTILINE
        ):
            if fence.start() < span[0] < fence.end():
                raise ValueError(f"{arm} host starts inside a code block")
        locators.check_edges(host)
        locators.locators(host, source)
        if occurrence is not None:
            start, end = int(occurrence[f"{arm}_start"]), int(occurrence[f"{arm}_end"])
            if not (span[0] <= start and end <= span[1]):
                raise ValueError(f"{arm} host does not contain the reviewed occurrence")
        anchor = arm_field(entry, "anchor", arm)
        if not isinstance(anchor, str) or not anchor:
            raise ValueError(f"{arm} anchor missing")
        check_anchor(anchor, source, span, arm)
        quote = arm_field(entry, "evidence", arm)
        if entry.get("gate") == "pass" and not (
            isinstance(quote, str) and quote.strip()
        ):
            raise ValueError(f"{arm} gate evidence missing")
        if isinstance(quote, str) and quote.strip():
            check_evidence(quote, source, span, arm)
        result[f"evidence_{arm}"] = quote or ""
        result[f"host_{arm}"] = host
        result[f"anchor_{arm}"] = anchor
    for name in ("question", "correct", "foil_1"):
        if not str(entry.get(name, "")).strip():
            raise ValueError(f"Probe field {name} missing")
    gate = entry.get("gate")
    if gate not in {"pass", "fail"}:
        raise ValueError("gate must be pass or fail")
    if gate == "fail" and (
        entry.get("failed_arm") not in {"explicit", "implicit", "both"}
        or not entry.get("reason_gate")
    ):
        raise ValueError("Gate failures need failed_arm and reason_gate")
    return result


def load_candidates(review_dir: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for name in ("o1_review.csv", "o2_review.csv"):
        with (review_dir / name).open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                rows[row["instance_id"]] = row
    return rows


def legacy_mapping(
    candidates: dict[str, dict[str, str]], legacy_rows: list[dict[str, str]]
) -> dict[str, dict[str, str]]:
    """Map each occurrence to its legacy expression row and occurrence rank."""
    legacy = {
        (r["specimen_id"], r["relation_type"], r["expression"]): r for r in legacy_rows
    }
    ranks: dict[tuple[str, str, str], int] = {}
    mapped: dict[str, dict[str, str]] = {}
    for identifier in sorted(
        candidates,
        key=lambda i: (
            candidates[i]["specimen_id"],
            int(candidates[i]["explicit_start"]),
        ),
    ):
        row = candidates[identifier]
        key = (row["specimen_id"], row["relation_type"], row["expression"])
        if key not in legacy:
            raise ValueError(f"{identifier} has no legacy expression row")
        ranks[key] = ranks.get(key, 0) + 1
        old = legacy[key]
        mapped[identifier] = {
            "legacy_id": old["instance_id"],
            "legacy_accept": old["accept"],
            "legacy_reason": old["rejection_reason"],
            "occurrence_rank": str(ranks[key]),
        }
    return mapped


def build(
    authoring_dir: Path = AUTHORING,
    instruments: Path = INSTRUMENTS,
    review_dir: Path = REPO_ROOT / "build" / "occurrence-review",
    corpus: Path = REPO_ROOT / "corpus",
    date: str | None = None,
    write: bool = True,
    only: set[str] | None = None,
) -> dict[str, Any]:
    date = date or datetime.datetime.now(datetime.UTC).date().isoformat()
    with (corpus / "specimens.csv").open(encoding="utf-8") as handle:
        specimens = {
            row["specimen_id"]: row["source_path"] for row in csv.DictReader(handle)
        }
    candidates = load_candidates(review_dir)
    legacy_rows: list[dict[str, str]] = []
    for name in ("o1_review.csv", "o2_review.csv"):
        with (instruments / name).open(encoding="utf-8", newline="") as handle:
            legacy_rows += list(csv.DictReader(handle))
    mapping = legacy_mapping(candidates, legacy_rows)
    with (instruments / "instances.csv").open(encoding="utf-8", newline="") as handle:
        current = list(csv.DictReader(handle))
    relations = {
        row["instance_id"]: row
        for row in current
        if row["relation_type"].startswith("R")
    }

    errors: list[str] = []
    instances: list[dict[str, str]] = []
    probes: list[dict[str, str]] = []
    exclusions: list[dict[str, str]] = []
    decisions: list[dict[str, str]] = []
    evidence: list[dict[str, str]] = []
    seen: set[str] = set()
    if only is not None:
        write = False
        candidates = {k: v for k, v in candidates.items() if v["specimen_id"] in only}
        relations = {k: v for k, v in relations.items() if v["specimen_id"] in only}
    for sid in sorted(only or specimens):
        path = authoring_dir / f"{sid}.toml"
        if not path.exists():
            errors.append(f"{sid}: authoring file missing")
            continue
        document = tomllib.loads(path.read_text(encoding="utf-8"))
        sources = Sources(
            (corpus / "explicit" / specimens[sid]).read_text(encoding="utf-8"),
            (corpus / "implicit" / specimens[sid]).read_text(encoding="utf-8"),
        )
        entries = [("candidate", e) for e in document.get("candidate", [])] + [
            ("relation", e) for e in document.get("relation", [])
        ]
        for kind, entry in entries:
            identifier = entry.get("id", "")
            if identifier in seen:
                errors.append(f"{identifier}: duplicate authoring entry")
                continue
            seen.add(identifier)
            occurrence = candidates.get(identifier) if kind == "candidate" else None
            base = relations.get(identifier) if kind == "relation" else occurrence
            if base is None or base["specimen_id"] != sid:
                errors.append(f"{identifier}: unknown {kind} for {sid}")
                continue
            if kind == "candidate":
                assert occurrence is not None
                decision = entry.get("decision")
                reason = str(entry.get("reason", "")).strip()
                if decision not in {"accept", "reject"} or not reason:
                    errors.append(f"{identifier}: decision and reason required")
                    continue
                if decision == "reject" and reason.split(":")[0] not in REJECTION_CODES:
                    errors.append(
                        f"{identifier}: rejection reason needs a code from {sorted(REJECTION_CODES)}"
                    )
                    continue
                decisions.append(
                    {
                        "instance_id": identifier,
                        "specimen_id": sid,
                        "relation_type": occurrence["relation_type"],
                        "expression": occurrence["expression"],
                        **{
                            k: occurrence[k]
                            for k in (
                                "explicit_start",
                                "explicit_end",
                                "implicit_start",
                                "implicit_end",
                            )
                        },
                        **mapping[identifier],
                        "decision": decision,
                        "reason": reason,
                        "reviewed": date,
                    }
                )
                if decision == "reject":
                    continue
            if entry.get("invalid"):
                # Not a genuine instance in either arm: excluded before lock with
                # its original (legacy) row retained, never given a fabricated probe.
                if (
                    kind != "relation"
                    or entry.get("gate") != "fail"
                    or entry.get("failed_arm") != "both"
                    or not entry.get("reason_gate")
                ):
                    errors.append(
                        f"{identifier}: invalid instances need gate=fail, failed_arm=both, reason_gate"
                    )
                    continue
                assert base is not None
                instances.append(
                    {name: base[name] for name in INSTANCE_FIELDS}
                    | {
                        "notes": f"{base['notes']}; reviewed {date}: invalid instance, excluded"
                    }
                )
                exclusions.append(
                    {
                        "instance_id": identifier,
                        "reason": entry["reason_gate"],
                        "failed_arm": "both",
                        "date": date,
                    }
                )
                evidence += [
                    {
                        "instance_id": identifier,
                        "arm": arm,
                        "answer": "",
                        "evidence": "",
                        "gate": "fail",
                    }
                    for arm in ("explicit", "implicit")
                ]
                continue
            try:
                compiled = compile_instance(entry, sources, occurrence)
            except ValueError as error:
                errors.append(f"{identifier}: {error}")
                continue
            if kind == "candidate":
                assert occurrence is not None
                legacy = mapping[identifier]
                notes = (
                    f"Occurrence '{occurrence['expression']}' at explicit A0 chars "
                    f"[{occurrence['explicit_start']},{occurrence['explicit_end']}), implicit "
                    f"[{occurrence['implicit_start']},{occurrence['implicit_end']}); legacy "
                    f"{legacy['legacy_id']} ({legacy['legacy_accept']}, occurrence "
                    f"{legacy['occurrence_rank']}); reviewed {date}: {entry['reason']}"
                )
                relation_type, demark_rule = occurrence["relation_type"], ""
            else:
                assert base is not None
                notes = base["notes"] + (
                    f"; reviewed {date}: {entry['reason']}"
                    if entry.get("reason")
                    else ""
                )
                relation_type, demark_rule = base["relation_type"], base["demark_rule"]
            instances.append(
                {
                    "instance_id": identifier,
                    "specimen_id": sid,
                    "relation_type": relation_type,
                    "anchor_explicit": compiled["anchor_explicit"],
                    "anchor_implicit": compiled["anchor_implicit"],
                    "host_passage_explicit": compiled["host_explicit"],
                    "host_passage_implicit": compiled["host_implicit"],
                    "demark_rule": demark_rule,
                    "notes": notes,
                }
            )
            report = lint_probes.LinterReport()
            lint_probes._check_distinctive_strings(
                report,
                {
                    "probe_id": identifier,
                    "_specimen_id": sid,
                    "question": entry["question"],
                    "correct_answer": entry["correct"],
                    "foil_1": entry["foil_1"],
                    "foil_2": entry.get("foil_2", ""),
                    "superseded_answer": entry.get("superseded_answer", ""),
                },
                {sid: sources.explicit},
                {sid: sources.implicit},
            )
            lint_probes._check_foils(
                report,
                {
                    "probe_id": identifier,
                    "correct_answer": entry["correct"],
                    "foil_1": entry["foil_1"],
                    "foil_2": entry.get("foil_2", ""),
                },
            )
            errors += report.errors
            if entry["gate"] == "pass":
                version = bool(entry.get("version_change", False))
                probes.append(
                    {
                        "probe_id": f"P-{identifier}",
                        "instance_id": identifier,
                        "question": entry["question"],
                        "correct_answer": entry["correct"],
                        "foil_1": entry["foil_1"],
                        "foil_2": entry.get("foil_2", ""),
                        "version_change": "true" if version else "false",
                        "superseded_answer": entry.get("superseded_answer", "")
                        if version
                        else "",
                        "superseded_source": entry.get("superseded_source", "")
                        if version
                        else "",
                    }
                )
            else:
                exclusions.append(
                    {
                        "instance_id": identifier,
                        "reason": f"{entry['reason_gate']} (probe: {entry['question']} | {entry['correct']})",
                        "failed_arm": entry["failed_arm"],
                        "date": date,
                    }
                )
            for arm in ("explicit", "implicit"):
                evidence.append(
                    {
                        "instance_id": identifier,
                        "arm": arm,
                        "answer": entry["correct"] if entry["gate"] == "pass" else "",
                        "evidence": compiled.get(f"evidence_{arm}", ""),
                        "gate": "fail"
                        if entry["gate"] == "fail"
                        and entry["failed_arm"] in {arm, "both"}
                        else "pass",
                    }
                )
    missing_candidates = sorted(set(candidates) - seen)
    missing_relations = sorted(set(relations) - seen)
    if missing_candidates:
        errors.append(
            f"{len(missing_candidates)} occurrence candidates unreviewed, e.g. {missing_candidates[:3]}"
        )
    if missing_relations:
        errors.append(
            f"{len(missing_relations)} relation instances unauthored, e.g. {missing_relations[:3]}"
        )
    summary = {
        "errors": errors,
        "instances": len(instances),
        "probes": len(probes),
        "exclusions": len(exclusions),
        "candidates_accepted": sum(d["decision"] == "accept" for d in decisions),
        "candidates_rejected": sum(d["decision"] == "reject" for d in decisions),
    }
    if errors or not write:
        return summary
    order = {"R1": 0, "R2": 1, "R3": 2, "R4": 3, "O1": 4, "O2": 5}
    instances.sort(
        key=lambda r: (r["specimen_id"], order[r["relation_type"]], r["instance_id"])
    )
    probes.sort(key=lambda r: r["instance_id"])
    outputs = {
        "instances.csv": (INSTANCE_FIELDS, instances),
        "probes.csv": (lint_probes.PROBES_HEADERS, probes),
        "gate_exclusions.csv": (lint_probes.EXCLUSIONS_HEADERS, exclusions),
        "occurrence_decisions.csv": (DECISION_FIELDS, decisions),
        "gate_evidence.csv": (EVIDENCE_FIELDS, evidence),
    }
    staged = []
    for name, (fields, rows) in outputs.items():
        temporary = instruments / f".{name}.tmp"
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        staged.append((temporary, instruments / name))
    for temporary, target in staged:
        os.replace(temporary, target)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate without writing")
    parser.add_argument("--date", default=None, help="review date recorded in outputs")
    parser.add_argument("--only", nargs="*", help="validate only these specimens")
    args = parser.parse_args()
    only = set(args.only) if args.only else None
    summary = build(date=args.date, write=not args.check, only=only)
    errors = summary.pop("errors")
    for error in errors:
        print(f"ERROR: {error}")
    print(summary)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
