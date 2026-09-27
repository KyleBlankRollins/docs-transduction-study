"""UNPLANNED exploratory diagnostics for M1-AI (not pre-specified; see DESIGN).

Requested by the maintainer on 2026-09-27 after the pre-specified results were
seen, to test whether the implicit arm's higher scores reflect quote
verifiability rather than survival of the relation. Outputs go only under
``analysis/exploratory/`` and never replace the pre-specified tables.

1. ``correctness_by_stage_arm.csv``: right answer (score 2 or 3) versus not
   (0 or 1), with the explicit-minus-implicit gap per stage.
2. ``support_breakdown_by_stage_arm.csv``: how correct answers were supported:
   exact quote, quote verified only after A7 normalization, explicit quote
   that could not be verified, or support the evaluator itself marked inferred.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from docs_transduction_study import analysis

LABEL = (
    "UNPLANNED exploratory analysis (not pre-specified), run 2026-09-27 after the "
    "pre-specified M1-AI results were seen. Model-conditioned; A7 scoring."
)
STAGES = ("A1", "A2", "A3", "A4")
ARMS = ("explicit", "implicit")
SUPPORT = ("exact_quote", "normalized_quote", "unverified_quote", "inferred")


def classify(record: dict[str, Any]) -> str:
    """How a correct (score 2-3) answer was supported."""
    flags = record.get("flags", [])
    if record["score"] == 3:
        return (
            "normalized_quote"
            if "quote_verified_after_normalization" in flags
            else "exact_quote"
        )
    if "explicit_quote_unverified" in flags:
        return "unverified_quote"
    return "inferred"


def diagnostics(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    first = [r for r in records if r["pass_number"] == 1]
    correct: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    support: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for record in first:
        _, arm, stage = record["assignment_id"].split("|")
        right = record["score"] >= 2
        correct[(stage, arm)]["n"] += 1
        correct[(stage, arm)]["correct"] += right
        if right:
            support[(stage, arm)][classify(record)] += 1
    rows, gaps, breakdown = [], [], []
    for stage in STAGES:
        rates = {}
        for arm in ARMS:
            counts = correct[(stage, arm)]
            rate = counts["correct"] / counts["n"] if counts["n"] else None
            rates[arm] = rate
            rows.append(
                {
                    "stage": stage,
                    "arm": arm,
                    "n": counts["n"],
                    "correct": counts["correct"],
                    "rate": rate,
                }
            )
            total = sum(support[(stage, arm)].values())
            breakdown.append(
                {
                    "stage": stage,
                    "arm": arm,
                    "correct": total,
                    **{kind: support[(stage, arm)][kind] for kind in SUPPORT},
                    **{
                        f"{kind}_share": (
                            support[(stage, arm)][kind] / total if total else None
                        )
                        for kind in SUPPORT
                    },
                }
            )
        explicit, implicit = rates["explicit"], rates["implicit"]
        gap = None if explicit is None or implicit is None else explicit - implicit
        gaps.append(
            {
                "stage": stage,
                "explicit_rate": rates["explicit"],
                "implicit_rate": rates["implicit"],
                "gap": gap,
            }
        )
    return {"correctness": rows, "correctness_gap": gaps, "support": breakdown}


def write(out: Path, tables: dict[str, list[dict[str, Any]]]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    names = {
        "correctness": "correctness_by_stage_arm.csv",
        "correctness_gap": "correctness_gap_by_stage.csv",
        "support": "support_breakdown_by_stage_arm.csv",
    }
    for key, name in names.items():
        with (out / name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=list(tables[key][0]), lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(tables[key])
    (out / "README.md").write_text(
        f"# Quote diagnostics\n\n{LABEL}\n\n{__doc__}\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coding-dir", type=Path, default=Path("coding"))
    parser.add_argument(
        "--out", type=Path, default=Path("analysis/exploratory/quote_diagnostics")
    )
    args = parser.parse_args()
    tables = diagnostics(analysis.load_records(args.coding_dir, "m1_ai_a7_records"))
    write(args.out, tables)
    print(json.dumps({"label": LABEL, "out": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
