"""Pre-specified exploratory M1-AI analysis (amendment A3), gated on repeatability.

Every output is labeled exploratory and model-conditioned: M1-AI is not M1a or
M1b, and AI repeatability is not human reliability or validity. The gate
requires complete first-pass coverage of the locked assignments, the complete
seed-selected repeat sample, isolation evidence on every record, one evaluator
configuration, and unweighted Cohen's kappa >= 0.6. When the gate fails only an
engineering/failure report is written; substantive tables are withheld.

Pre-specified outputs (DESIGN analysis plan, adapted to M1-AI):
H1 arm x stage distributions, means, and explicit-minus-implicit gaps, pooled and
per specimen; H2 survival by observed type (O1, O2) x stage; R3 split by marking
device (D3, D4), never pooled; H3 Corrupted:Absent among non-Preserved A4
scores, overall and by arm and ``spans_chunks``. Anything else belongs under
``analysis/exploratory/``.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from docs_transduction_study import coding_ai

LABEL = (
    "Exploratory, model-conditioned M1-AI results (amendment A3). Not M1a or M1b; "
    "AI repeatability is not human reliability or validity."
)
ARMS = ("explicit", "implicit")
STAGES = ("A1", "A2", "A3", "A4")
SCORES = (0, 1, 2, 3)


def load_records(
    path: Path, records_dir: str = coding_ai.RECORDS_DIR
) -> list[dict[str, Any]]:
    """Load retained JSON records (the source of truth, not the CSV summary).

    ``m1_ai_records`` holds strict-protocol records; ``m1_ai_a7_records`` holds
    amendment-A7 rescoring of the retained answers.
    """
    return [
        json.loads(item.read_text(encoding="utf-8"))
        for item in sorted((path / records_dir).glob("*.json"))
    ]


def gate(
    records: list[dict[str, Any]], expected_ids: list[str], seed: str
) -> dict[str, Any]:
    """Evaluate the fail-closed gate; never raises for data problems."""
    reasons: list[str] = []
    first = {r["opaque_id"]: r["score"] for r in records if r["pass_number"] == 1}
    second = {r["opaque_id"]: r["score"] for r in records if r["pass_number"] == 2}
    missing = sorted(set(expected_ids) - set(first))
    foreign = sorted(set(first) - set(expected_ids))
    if missing:
        reasons.append(f"{len(missing)} first-pass assignments missing")
    if foreign:
        reasons.append(f"{len(foreign)} records outside the locked assignments")
    if not all(r.get("isolation_verified") for r in records):
        reasons.append("records without isolation evidence")
    configurations = {json.dumps(r["configuration"], sort_keys=True) for r in records}
    if len(configurations) > 1:
        reasons.append("more than one evaluator configuration")
    kappa: dict[str, Any] | None = None
    if not missing and not foreign and records:
        sample = coding_ai.repeat_sample(sorted(expected_ids), seed)
        try:
            kappa = coding_ai.repeatability(
                first,
                second,
                sample,
                expected_ids=sorted(expected_ids),
                seed=seed,
                isolation_verified=not reasons,
            )
        except ValueError as error:
            reasons.append(str(error))
    if kappa is None and not reasons:
        reasons.append("no records")
    if kappa is not None:
        if kappa["kappa"] is None:
            reasons.append("kappa undefined")
        elif kappa["kappa"] < 0.6:
            reasons.append(f"kappa {kappa['kappa']:.3f} below 0.6")
    return {
        "first_pass_records": len(first),
        "repeat_records": len(second),
        "expected_first_pass": len(expected_ids),
        "kappa": kappa["kappa"] if kappa else None,
        "repeat_sample_size": kappa["sample_size"] if kappa else None,
        "failures": reasons,
        "substantive_findings_allowed": not reasons,
    }


def _summary(scores: list[int]) -> dict[str, Any]:
    counts = Counter(scores)
    return {
        "n": len(scores),
        **{f"score_{s}": counts.get(s, 0) for s in SCORES},
        "mean": sum(scores) / len(scores) if scores else None,
    }


def survival_table(
    rows: list[dict[str, Any]], by: tuple[str, ...]
) -> list[dict[str, Any]]:
    """Distribution and mean per group; groups with no rows are listed with n=0."""
    groups: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in by)].append(row["score"])
    keys = sorted(groups)
    return [
        {**dict(zip(by, key, strict=True)), **_summary(groups[key])} for key in keys
    ]


def gaps(table: list[dict[str, Any]], within: tuple[str, ...]) -> list[dict[str, Any]]:
    """Explicit minus implicit mean per stage (and grouping); None when a side is empty."""
    index = {tuple(row[k] for k in (*within, "arm")): row for row in table}
    result = []
    for key in sorted({tuple(row[k] for k in within) for row in table}):
        explicit = index.get((*key, "explicit"))
        implicit = index.get((*key, "implicit"))
        mean_e = explicit["mean"] if explicit else None
        mean_i = implicit["mean"] if implicit else None
        result.append(
            {
                **dict(zip(within, key, strict=True)),
                "explicit_mean": mean_e,
                "implicit_mean": mean_i,
                "gap": None if mean_e is None or mean_i is None else mean_e - mean_i,
            }
        )
    return result


def corrupted_absent(
    rows: list[dict[str, Any]], by: tuple[str, ...]
) -> list[dict[str, Any]]:
    """H3: among non-Preserved A4 scores, Corrupted (0) versus Absent (1)."""
    groups: dict[tuple[Any, ...], Counter[int]] = defaultdict(Counter)
    for row in rows:
        if row["stage"] == "A4" and row["score"] != 3:
            groups[tuple(row[k] for k in by)][row["score"]] += 1
    result = []
    # Missing span flags stay visible as their own (None) group.
    for key in sorted(groups, key=lambda k: tuple(str(v) for v in k)):
        counts = groups[key]
        result.append(
            {
                **dict(zip(by, key, strict=True)),
                "non_preserved": sum(counts.values()),
                "corrupted": counts[0],
                "absent": counts[1],
                "degraded": counts[2],
                "corrupted_to_absent": counts[0] / counts[1] if counts[1] else None,
            }
        )
    return result


def join(
    records: list[dict[str, Any]],
    instances: dict[str, dict[str, str]],
    spans: dict[tuple[str, str], bool],
) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        if record["pass_number"] != 1:
            continue
        instance_id, arm, stage = record["assignment_id"].split("|")
        instance = instances[instance_id]
        relation = instance["relation_type"]
        rows.append(
            {
                "instance_id": instance_id,
                "specimen_id": instance["specimen_id"],
                "relation": relation,
                "device": instance["demark_rule"] if relation == "R3" else "",
                "arm": arm,
                "stage": stage,
                "score": record["score"],
                "spans_chunks": spans.get((instance_id, arm))
                if stage == "A4"
                else None,
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def analyze(
    coding_dir: Path,
    instances: dict[str, dict[str, str]],
    expected_ids: list[str],
    seed: str,
    spans: dict[tuple[str, str], bool],
    out: Path,
    records_dir: str = coding_ai.RECORDS_DIR,
) -> dict[str, Any]:
    records = load_records(coding_dir, records_dir)
    status = gate(records, expected_ids, seed)
    out.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"label": LABEL, "scoring": records_dir, "gate": status}
    if not status["substantive_findings_allowed"]:
        report["engineering"] = {
            "records": len(records),
            "scores_withheld": True,
            "note": "Substantive findings are blocked; publish this limitation or failure.",
        }
        (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
    rows = join(records, instances, spans)
    dist_fields = ["n", *[f"score_{s}" for s in SCORES], "mean"]
    tables: dict[str, tuple[list[dict[str, Any]], list[str]]] = {}
    pooled = survival_table(rows, ("stage", "arm"))
    tables["h1_pooled"] = (pooled, ["stage", "arm", *dist_fields])
    tables["h1_gap_pooled"] = (
        gaps(pooled, ("stage",)),
        ["stage", "explicit_mean", "implicit_mean", "gap"],
    )
    per_specimen = survival_table(rows, ("specimen_id", "stage", "arm"))
    tables["h1_per_specimen"] = (
        per_specimen,
        ["specimen_id", "stage", "arm", *dist_fields],
    )
    tables["h1_gap_per_specimen"] = (
        gaps(per_specimen, ("specimen_id", "stage")),
        ["specimen_id", "stage", "explicit_mean", "implicit_mean", "gap"],
    )
    observed = [row for row in rows if row["relation"] in {"O1", "O2"}]
    tables["h2_observed"] = (
        survival_table(observed, ("relation", "stage", "arm")),
        ["relation", "stage", "arm", *dist_fields],
    )
    force = [row for row in rows if row["relation"] == "R3"]
    r3 = survival_table(force, ("device", "stage", "arm"))
    for device in ("D3", "D4"):
        if not any(row["device"] == device for row in r3):
            r3.append(
                {
                    "device": device,
                    "stage": "",
                    "arm": "",
                    "n": 0,
                    **{f"score_{s}": 0 for s in SCORES},
                    "mean": None,
                }
            )
    tables["r3_by_device"] = (r3, ["device", "stage", "arm", *dist_fields])
    h3_fields = [
        "non_preserved",
        "corrupted",
        "absent",
        "degraded",
        "corrupted_to_absent",
    ]
    tables["h3_overall"] = (corrupted_absent(rows, ()), h3_fields)
    tables["h3_by_arm_spans"] = (
        corrupted_absent(rows, ("arm", "spans_chunks")),
        ["arm", "spans_chunks", *h3_fields],
    )
    for name, (table, fields) in tables.items():
        _write_csv(out / f"{name}.csv", table, fields)
    report["tables"] = sorted(tables)
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    from docs_transduction_study import study_pipeline

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coding-dir", type=Path, default=Path("coding"))
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    parser.add_argument("--out", type=Path, default=Path("analysis/m1_ai"))
    parser.add_argument("--gate-only", action="store_true")
    parser.add_argument(
        "--records",
        default="m1_ai_a7_records",
        help="m1_ai_a7_records (amendment A7, primary) or m1_ai_records (strict)",
    )
    args = parser.parse_args()
    instrument = study_pipeline.load_instrument()
    plan = study_pipeline.assignment_plan(instrument)
    expected = [plan["opaque"][identifier] for identifier in plan["order"]]
    if args.gate_only:
        print(
            json.dumps(
                gate(
                    load_records(args.coding_dir, args.records),
                    expected,
                    instrument["seed"],
                ),
                indent=2,
            )
        )
        return
    spans = {}
    assignments = args.artifacts / "anchor-assignments.json"
    if assignments.exists():
        for record in json.loads(assignments.read_text(encoding="utf-8")):
            for arm in ARMS:
                spans[(record["instance_id"], arm)] = record[arm]["spans_chunks"]
    instances = {row["instance_id"]: row for row in instrument["instances"]}
    report = analyze(
        args.coding_dir,
        instances,
        expected,
        instrument["seed"],
        spans,
        args.out,
        args.records,
    )
    print(json.dumps(report["gate"], indent=2))


if __name__ == "__main__":
    main()
