"""Pre-specified evaluator replication comparison (amendment A9).

Fixed before any replication answer was seen. For each stage A1-A4 and each
evaluator, it reports the pooled explicit-minus-implicit A7 mean gap (from the
pre-specified ``h1_gap_pooled.csv``) and the first-pass correctness gap (score
2-3 versus 0-1), with whether the two evaluators' signs agree. Evaluators are
never pooled; disagreements are reported, not reconciled. A side whose gate
blocks substantive findings is reported as blocked and not compared.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from docs_transduction_study import analysis, exploratory

LABEL = (
    "Pre-specified evaluator replication comparison (amendment A9). Exploratory, "
    "model-conditioned M1-AI; evaluators are not pooled."
)
STAGES = exploratory.STAGES


def sign(value: float | None) -> int | None:
    if value is None:
        return None
    return (value > 0) - (value < 0)


def side(coding: Path, analysis_dir: Path) -> dict[str, Any]:
    report = json.loads((analysis_dir / "report.json").read_text(encoding="utf-8"))
    if not report["gate"]["substantive_findings_allowed"]:
        return {"blocked": True}
    with (analysis_dir / "h1_gap_pooled.csv").open(encoding="utf-8") as handle:
        mean_gap = {row["stage"]: float(row["gap"]) for row in csv.DictReader(handle)}
    tables = exploratory.diagnostics(analysis.load_records(coding, "m1_ai_a7_records"))
    correct_gap = {row["stage"]: row["gap"] for row in tables["correctness_gap"]}
    return {"blocked": False, "mean_gap": mean_gap, "correctness_gap": correct_gap}


def compare(reference: dict[str, Any], replication: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "label": LABEL,
        "reference_blocked": reference["blocked"],
        "replication_blocked": replication["blocked"],
        "rows": [],
    }
    if reference["blocked"] or replication["blocked"]:
        return result
    for measure in ("mean_gap", "correctness_gap"):
        for stage in STAGES:
            a = reference[measure].get(stage)
            b = replication[measure].get(stage)
            agree = None if sign(a) is None or sign(b) is None else sign(a) == sign(b)
            result["rows"].append(
                {
                    "measure": measure,
                    "stage": stage,
                    "reference_gap": a,
                    "replication_gap": b,
                    "signs_agree": agree,
                }
            )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-coding", type=Path, default=Path("coding"))
    parser.add_argument(
        "--reference-analysis", type=Path, default=Path("analysis/m1_ai_a7")
    )
    parser.add_argument("--replication-coding", type=Path, required=True)
    parser.add_argument("--replication-analysis", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = compare(
        side(args.reference_coding, args.reference_analysis),
        side(args.replication_coding, args.replication_analysis),
    )
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "replication.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
