"""UNPLANNED exploratory M1-AI analyses E1-E7 (analysis/exploratory/PLAN.md).

Implements the plan committed before any of these quantities was computed.
Definitions, statistics, and reading rules follow the plan; anything outside
it belongs elsewhere and must be labelled as outside the plan.

Data: first-pass A7 records per evaluator, joined to the retained instances.
Gaps are explicit minus implicit within complete instance-stage pairs.
Uncertainty is a page-clustered bootstrap (12 specimens resampled with
replacement, 10,000 resamples, seed from SHA-256 of the plan's seed string);
every gap also reports per-specimen sign counts. No p-values.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import random
import subprocess
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docs_transduction_study import analysis

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN = "analysis/exploratory/PLAN.md"
SEED_STRING = "exploratory-plan-2026-11-18"
RESAMPLES = 10_000
ROBUST_MIN_SPECIMENS = 8
ABSENT_SAMPLE = 20
STAGES = analysis.STAGES
ARMS = analysis.ARMS
SCORES = analysis.SCORES
RELATIONS = ("R1", "R2", "R3", "R4", "O1", "O2")
SMALL = {"R4"}
EVALUATORS = {
    "glm-5.3-flash": Path("coding"),
    "claude-sonnet-5-5": Path("coding/claude-sonnet-5-5"),
}
LABEL = (
    "UNPLANNED exploratory analysis (not pre-specified); plan fixed at commit {sha} "
    "before computation. Model-conditioned M1-AI, A7 scoring; evaluators not pooled."
)

Row = dict[str, Any]
Pair = dict[str, Any]


# ── Outcomes ───────────────────────────────────────────────────────────────


def correct(score: int) -> int:
    return int(score >= 2)


def absent(score: int) -> int:
    return int(score == 1)


def corrupted(score: int) -> int:
    return int(score == 0)


def at_least(k: int) -> Callable[[int], int]:
    return lambda score: int(score >= k)


PAIRED_OUTCOMES: dict[str, Callable[[int], int]] = {
    "score": lambda s: s,
    "correct": correct,
    "absent": absent,
    "corrupted": corrupted,
}
# Score = [s>=1] + [s>=2] + [s>=3], so these three gaps sum to the score gap.
BOUNDARIES = {"0|1": at_least(1), "1|2": at_least(2), "2|3": at_least(3)}


# ── Pairs ──────────────────────────────────────────────────────────────────


def make_pairs(rows: list[Row]) -> tuple[list[Pair], list[dict[str, str]]]:
    """Complete instance-stage pairs, and the incomplete ones (never imputed)."""
    cells: dict[tuple[str, str], dict[str, Row]] = defaultdict(dict)
    for row in rows:
        cells[(row["instance_id"], row["stage"])][row["arm"]] = row
    pairs, incomplete = [], []
    for (instance_id, stage), arms in sorted(cells.items()):
        if set(arms) != set(ARMS):
            incomplete.append(
                {
                    "instance_id": instance_id,
                    "stage": stage,
                    "missing": ",".join(sorted(set(ARMS) - set(arms))),
                }
            )
            continue
        first = arms["explicit"]
        pairs.append(
            {
                "instance_id": instance_id,
                "specimen_id": first["specimen_id"],
                "relation": first["relation"],
                "group": "manipulated" if first["relation"][0] == "R" else "observed",
                "stage": stage,
                "explicit": arms["explicit"]["score"],
                "implicit": arms["implicit"]["score"],
            }
        )
    return pairs, incomplete


def all_instance_stage(rows: list[Row]) -> set[tuple[str, str]]:
    return {(r["instance_id"], r["stage"]) for r in rows}


# ── Clustered statistics ───────────────────────────────────────────────────


@dataclass
class Stat:
    """A statistic built from per-specimen additive components.

    ``parts[specimen]`` holds component sums; ``combine`` maps summed components
    to the statistic (``None`` when undefined, e.g. an empty denominator).
    """

    parts: dict[str, list[float]]
    combine: Callable[[list[float]], float | None]
    width: int


def _total(vectors: Iterable[list[float]], width: int) -> list[float]:
    total = [0.0] * width
    for vector in vectors:
        for index, value in enumerate(vector):
            total[index] += value
    return total


class Bootstrap:
    """One shared set of specimen resamples, reused by every statistic."""

    def __init__(self, specimens: list[str], resamples: int, seed_string: str):
        self.specimens = sorted(specimens)
        rng = random.Random(int(hashlib.sha256(seed_string.encode()).hexdigest(), 16))
        k = len(self.specimens)
        self.draws = [[rng.randrange(k) for _ in range(k)] for _ in range(resamples)]

    def summarize(self, stat: Stat) -> dict[str, Any]:
        width = stat.width
        point = stat.combine(_total(stat.parts.values(), width))
        values: list[float] = []
        undefined = 0
        zero = [0.0] * width
        vectors = [stat.parts.get(s, zero) for s in self.specimens]
        for draw in self.draws:
            value = stat.combine(_total((vectors[i] for i in draw), width))
            if value is None:
                undefined += 1
            else:
                values.append(value)
        values.sort()
        lo = values[int(0.025 * len(values))] if values else None
        hi = values[min(len(values) - 1, int(0.975 * len(values)))] if values else None
        signs = Counter(_sign(stat.combine(v)) for v in stat.parts.values())
        return {
            "point": point,
            "ci_low": lo,
            "ci_high": hi,
            "undefined_resamples": undefined,
            "specimens_negative": signs[-1],
            "specimens_zero": signs[0],
            "specimens_positive": signs[1],
            "specimens_undefined": signs[None],
            "specimens_without_data": len(set(self.specimens) - set(stat.parts)),
        }


def _sign(value: float | None) -> int | None:
    if value is None:
        return None
    if abs(value) < 1e-12:
        return 0
    return 1 if value > 0 else -1


def _ratio(num: float, den: float) -> float | None:
    return num / den if den else None


def paired_gap(pairs: list[Pair], outcome: Callable[[int], int]) -> Stat:
    parts: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for p in pairs:
        part = parts[p["specimen_id"]]
        part[0] += outcome(p["explicit"]) - outcome(p["implicit"])
        part[1] += 1
    return Stat(dict(parts), lambda t: _ratio(t[0], t[1]), 2)


def quotable_conditional(pairs: list[Pair]) -> Stat:
    """Paired gap in score 3, among pairs correct in both arms."""
    both = [p for p in pairs if correct(p["explicit"]) and correct(p["implicit"])]
    return paired_gap(both, at_least(3))


def quotable_unconditional(pairs: list[Pair]) -> Stat:
    """Share of score 3 among correct answers, explicit minus implicit."""
    parts: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    for p in pairs:
        part = parts[p["specimen_id"]]
        part[0] += p["explicit"] == 3
        part[1] += correct(p["explicit"])
        part[2] += p["implicit"] == 3
        part[3] += correct(p["implicit"])

    def combine(t: list[float]) -> float | None:
        e, i = _ratio(t[0], t[1]), _ratio(t[2], t[3])
        return None if e is None or i is None else e - i

    return Stat(dict(parts), combine, 4)


def difference_in_differences(first: Stat, second: Stat) -> Stat:
    """first minus second, resampled jointly by specimen."""
    w1, w2 = first.width, second.width
    parts = {}
    for s in set(first.parts) | set(second.parts):
        parts[s] = first.parts.get(s, [0.0] * w1) + second.parts.get(s, [0.0] * w2)

    def combine(t: list[float]) -> float | None:
        a, b = first.combine(t[:w1]), second.combine(t[w1:])
        return None if a is None or b is None else a - b

    return Stat(parts, combine, w1 + w2)


def outcome_stats(pairs: list[Pair]) -> dict[str, Stat]:
    stats = {name: paired_gap(pairs, fn) for name, fn in PAIRED_OUTCOMES.items()}
    stats["quotable_conditional"] = quotable_conditional(pairs)
    stats["quotable_unconditional"] = quotable_unconditional(pairs)
    return stats


# ── E1-E6 ──────────────────────────────────────────────────────────────────


def e1(pairs: list[Pair], boot: Bootstrap) -> list[Row]:
    out = []
    for stage in STAGES:
        here = [p for p in pairs if p["stage"] == stage]
        manipulated = outcome_stats([p for p in here if p["group"] == "manipulated"])
        observed = outcome_stats([p for p in here if p["group"] == "observed"])
        for outcome in manipulated:
            for quantity, stat in (
                ("G_R", manipulated[outcome]),
                ("G_O", observed[outcome]),
                (
                    "DiD",
                    difference_in_differences(manipulated[outcome], observed[outcome]),
                ),
            ):
                out.append(
                    {
                        "stage": stage,
                        "outcome": outcome,
                        "quantity": quantity,
                        **boot.summarize(stat),
                    }
                )
    return out


def e2_rates(rows: list[Row]) -> list[Row]:
    out = []
    for stage in STAGES:
        for arm in ARMS:
            scores = [
                r["score"] for r in rows if r["stage"] == stage and r["arm"] == arm
            ]
            n = len(scores)
            count = Counter(scores)
            right = count[2] + count[3]
            out.append(
                {
                    "stage": stage,
                    "arm": arm,
                    "n": n,
                    **{f"score_{s}": count[s] for s in SCORES},
                    "correct_rate": _ratio(right, n),
                    "quotable_among_correct": _ratio(count[3], right),
                    "absent_rate": _ratio(count[1], n),
                    "corrupted_rate": _ratio(count[0], n),
                }
            )
    return out


def e2_gaps(pairs: list[Pair], boot: Bootstrap) -> list[Row]:
    out = []
    for stage in STAGES:
        here = [p for p in pairs if p["stage"] == stage]
        stats = outcome_stats(here)
        stats.update(
            {f"boundary_{b}": paired_gap(here, fn) for b, fn in BOUNDARIES.items()}
        )
        for name, stat in stats.items():
            out.append(
                {
                    "stage": stage,
                    "outcome": name,
                    "n_pairs": len(here),
                    **boot.summarize(stat),
                }
            )
    return out


def e3(pairs: list[Pair]) -> list[Row]:
    out = []
    for stage in STAGES:
        for specimen in sorted({p["specimen_id"] for p in pairs}):
            here = [
                p for p in pairs if p["stage"] == stage and p["specimen_id"] == specimen
            ]
            if not here:
                continue
            n = len(here)
            out.append(
                {
                    "stage": stage,
                    "specimen_id": specimen,
                    "n_pairs": n,
                    "score_gap": sum(p["explicit"] - p["implicit"] for p in here) / n,
                    "correct_gap": sum(
                        correct(p["explicit"]) - correct(p["implicit"]) for p in here
                    )
                    / n,
                }
            )
    return out


def e5(rows: list[Row], pairs: list[Pair], boot: Bootstrap) -> dict[str, list[Row]]:
    score = {(r["instance_id"], r["arm"], r["stage"]): r["score"] for r in rows}
    instances = sorted({r["instance_id"] for r in rows})
    transitions = []
    for arm in ARMS:
        for a, b in itertools.pairwise(STAGES):
            counts: Counter[tuple[int, int]] = Counter()
            for i in instances:
                if (i, arm, a) in score and (i, arm, b) in score:
                    counts[(score[(i, arm, a)], score[(i, arm, b)])] += 1
            for (x, y), n in sorted(counts.items()):
                transitions.append(
                    {
                        "arm": arm,
                        "from_stage": a,
                        "to_stage": b,
                        "from_score": x,
                        "to_score": y,
                        "n": n,
                    }
                )
    first_loss = []
    for arm in ARMS:
        for label, lost in (
            ("below_3", lambda s: s < 3),
            ("at_most_1", lambda s: s <= 1),
        ):
            counts2: Counter[str] = Counter()
            for i in instances:
                hit = next(
                    (
                        st
                        for st in STAGES
                        if (i, arm, st) in score and lost(score[(i, arm, st)])
                    ),
                    "never",
                )
                counts2[hit] += 1
            for stage in (*STAGES, "never"):
                first_loss.append(
                    {
                        "arm": arm,
                        "threshold": label,
                        "first_stage": stage,
                        "n": counts2[stage],
                    }
                )
    gap = {(p["instance_id"], p["stage"]): p["explicit"] - p["implicit"] for p in pairs}
    specimen = {p["instance_id"]: p["specimen_id"] for p in pairs}
    changes = [
        (i, gap[(i, "A4")] - gap[(i, "A1")])
        for i in sorted(specimen)
        if (i, "A1") in gap and (i, "A4") in gap
    ]
    distribution = Counter(c for _, c in changes)
    parts: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for i, c in changes:
        parts[specimen[i]][0] += c
        parts[specimen[i]][1] += 1
    summary = boot.summarize(Stat(dict(parts), lambda t: _ratio(t[0], t[1]), 2))
    widening = [{"change": c, "n": distribution[c]} for c in sorted(distribution)]
    widening.append({"change": "mean", "n": len(changes), **summary})
    return {"transitions": transitions, "first_loss": first_loss, "widening": widening}


def e6(rows: list[Row], pairs: list[Pair], boot: Bootstrap) -> dict[str, list[Row]]:
    gaps = []
    for relation in RELATIONS:
        for stage in STAGES:
            here = [
                p for p in pairs if p["relation"] == relation and p["stage"] == stage
            ]
            for name, stat in outcome_stats(here).items():
                gaps.append(
                    {
                        "relation": relation,
                        "stage": stage,
                        "outcome": name,
                        "n_pairs": len(here),
                        "too_small": relation in SMALL,
                        **boot.summarize(stat),
                    }
                )
    spans = []
    for arm in ARMS:
        for split in (True, False):
            here = [
                r
                for r in rows
                if r["stage"] == "A4" and r["arm"] == arm and r["spans_chunks"] is split
            ]
            n = len(here)
            spans.append(
                {
                    "arm": arm,
                    "spans_chunks": split,
                    "n": n,
                    "absent": sum(absent(r["score"]) for r in here),
                    "corrupted": sum(corrupted(r["score"]) for r in here),
                    "absent_rate": _ratio(sum(absent(r["score"]) for r in here), n),
                    "corrupted_rate": _ratio(
                        sum(corrupted(r["score"]) for r in here), n
                    ),
                }
            )
    return {"gaps": gaps, "spans": spans}


# ── E4 and robustness (both evaluators) ────────────────────────────────────


def kappa(pairs: list[tuple[int, int]], categories: Iterable[int]) -> float | None:
    count = len(pairs)
    if not count:
        return None
    observed = sum(a == b for a, b in pairs) / count
    first = Counter(a for a, _ in pairs)
    second = Counter(b for _, b in pairs)
    expected = sum(first[c] * second[c] for c in categories) / count**2
    return None if expected == 1 else (observed - expected) / (1 - expected)


def _key(row: Row) -> tuple[str, str, str]:
    return (row["instance_id"], row["arm"], row["stage"])


def e4(rows_by_evaluator: dict[str, list[Row]], boot: Bootstrap) -> dict[str, Any]:
    (name_a, rows_a), (name_b, rows_b) = rows_by_evaluator.items()
    a = {_key(r): r for r in rows_a}
    b = {_key(r): r for r in rows_b}
    shared = sorted(set(a) & set(b))
    both = [(a[k]["score"], b[k]["score"]) for k in shared]
    confusion = Counter(both)
    by_cell = []
    for stage in STAGES:
        for arm in ARMS:
            cell = [
                (a[k]["score"], b[k]["score"])
                for k in shared
                if k[1] == arm and k[2] == stage
            ]
            by_cell.append(
                {
                    "stage": stage,
                    "arm": arm,
                    "n": len(cell),
                    "agreement": _ratio(sum(x == y for x, y in cell), len(cell)),
                    "kappa": kappa(cell, SCORES),
                }
            )
    agreed = [a[k] for k in shared if a[k]["score"] == b[k]["score"]]
    agreed_pairs, _ = make_pairs(agreed)
    agreed_rows = e1(agreed_pairs, boot) + [
        {**r, "quantity": "pooled"} for r in e2_gaps(agreed_pairs, boot)
    ]
    return {
        "summary": {
            "evaluators": [name_a, name_b],
            "shared_assignments": len(shared),
            "agreement": _ratio(sum(x == y for x, y in both), len(both)),
            "kappa_score": kappa(both, SCORES),
            "kappa_correct": kappa([(correct(x), correct(y)) for x, y in both], (0, 1)),
            "agreed_assignments": len(agreed),
            "agreed_complete_pairs": len(agreed_pairs),
        },
        "confusion": [
            {f"{name_a}": x, f"{name_b}": y, "n": confusion[(x, y)]}
            for x in SCORES
            for y in SCORES
        ],
        "by_cell": by_cell,
        "agreed_gaps": agreed_rows,
    }


def robustness(results: dict[str, dict[str, list[Row]]]) -> list[Row]:
    """Plan rule: same sign under both evaluators and >= 8 of 12 specimens each."""
    names = list(results)
    out = []
    for table in ("e1", "e2_gaps", "e6_gaps"):
        keyed = []
        for name in names:
            keyed.append(
                {
                    tuple(
                        (k, row[k])
                        for k in ("relation", "stage", "outcome", "quantity")
                        if k in row
                    ): row
                    for row in results[name][table]
                }
            )
        for key in keyed[0]:
            if key not in keyed[1]:
                continue
            rows = [k[key] for k in keyed]
            signs = [_sign(r["point"]) for r in rows]
            sign = (
                signs[0] if len(set(signs)) == 1 and signs[0] not in (None, 0) else None
            )
            field = {-1: "specimens_negative", 1: "specimens_positive"}.get(sign or 0)
            support: list[int | None] = (
                [r[field] for r in rows] if field else [None] * len(rows)
            )
            robust = bool(field) and all(
                s is not None and s >= ROBUST_MIN_SPECIMENS for s in support
            )
            named_key: dict[str, Any] = dict(key)
            out.append(
                {
                    "table": table,
                    **named_key,
                    **{
                        f"point_{n}": r["point"]
                        for n, r in zip(names, rows, strict=True)
                    },
                    **{
                        f"specimens_with_sign_{n}": s
                        for n, s in zip(names, support, strict=True)
                    },
                    "same_sign": sign is not None,
                    "robust": robust,
                }
            )
    return out


# ── E7 ─────────────────────────────────────────────────────────────────────


def e7(rows_by_evaluator: dict[str, list[Row]]) -> list[Row]:
    """Case sheet: every Corrupted answer and 20 seeded Absent answers at A4."""
    cases = []
    for name, rows in rows_by_evaluator.items():
        for r in rows:
            if corrupted(r["score"]):
                cases.append(_case(name, r, "corrupted"))
        pool = [r for r in rows if r["stage"] == "A4" and absent(r["score"])]
        ranked = sorted(
            pool,
            key=lambda r: hashlib.sha256(
                f"{SEED_STRING}:absent-sample:{name}:{r['opaque_id']}".encode()
            ).hexdigest(),
        )
        cases.extend(_case(name, r, "absent_sample") for r in ranked[:ABSENT_SAMPLE])
    return cases


def _case(evaluator: str, row: Row, reason: str) -> Row:
    return {
        "evaluator": evaluator,
        "reason": reason,
        "opaque_id": row["opaque_id"],
        "instance_id": row["instance_id"],
        "relation": row["relation"],
        "arm": row["arm"],
        "stage": row["stage"],
        "score": row["score"],
        "category": "",
        "note": "",
        "reviewed_by_maintainer": "",
    }


# ── Driver ─────────────────────────────────────────────────────────────────


def load_rows(
    coding: Path,
    instances: dict[str, dict[str, str]],
    spans: dict[tuple[str, str], bool],
) -> list[Row]:
    records = [
        r
        for r in analysis.load_records(coding, "m1_ai_a7_records")
        if r["pass_number"] == 1
    ]
    joined = analysis.join(records, instances, spans)
    for row, record in zip(joined, records, strict=True):
        row["opaque_id"] = record["opaque_id"]
    return joined


def run_evaluator(rows: list[Row], boot: Bootstrap) -> dict[str, list[Row]]:
    pairs, incomplete = make_pairs(rows)
    tables: dict[str, list[Row]] = {
        "incomplete_pairs": incomplete,
        "e1": e1(pairs, boot),
        "e2_rates": e2_rates(rows),
        "e2_gaps": e2_gaps(pairs, boot),
        "e3": e3(pairs),
    }
    tables.update({f"e5_{k}": v for k, v in e5(rows, pairs, boot).items()})
    tables.update({f"e6_{k}": v for k, v in e6(rows, pairs, boot).items()})
    return tables


def write_csv(path: Path, rows: list[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        fields.extend(k for k in row if k not in fields)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields or ["empty"], lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def plan_commit(repo: Path = REPO_ROOT) -> str:
    sha = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", PLAN],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if not sha:
        raise RuntimeError("The plan is not committed; commit it before computing")
    return sha


def main() -> None:
    from docs_transduction_study import study_pipeline

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    parser.add_argument(
        "--out", type=Path, default=Path("analysis/exploratory/plan-2026-11")
    )
    parser.add_argument("--resamples", type=int, default=RESAMPLES)
    args = parser.parse_args()
    sha = plan_commit()
    instrument = study_pipeline.load_instrument()
    instances = {row["instance_id"]: row for row in instrument["instances"]}
    spans: dict[tuple[str, str], bool] = {}
    for record in json.loads(
        (args.artifacts / "anchor-assignments.json").read_text(encoding="utf-8")
    ):
        for arm in ARMS:
            spans[(record["instance_id"], arm)] = record[arm]["spans_chunks"]
    rows = {
        name: load_rows(path, instances, spans) for name, path in EVALUATORS.items()
    }
    specimens = sorted({row["specimen_id"] for row in instances.values()})
    boot = Bootstrap(specimens, args.resamples, SEED_STRING)
    results = {name: run_evaluator(r, boot) for name, r in rows.items()}
    for name, tables in results.items():
        for table, data in tables.items():
            write_csv(args.out / name / f"{table}.csv", data)
    combined = e4(rows, boot)
    (args.out / "combined").mkdir(parents=True, exist_ok=True)
    (args.out / "combined" / "e4_summary.json").write_text(
        json.dumps(combined["summary"], indent=2), encoding="utf-8"
    )
    for table in ("confusion", "by_cell", "agreed_gaps"):
        write_csv(args.out / "combined" / f"e4_{table}.csv", combined[table])
    write_csv(args.out / "combined" / "robustness.csv", robustness(results))
    write_csv(args.out / "combined" / "e7_cases.csv", e7(rows))
    label = LABEL.format(sha=sha)
    (args.out / "README.md").write_text(
        f"# Exploratory analyses E1-E7\n\n{label}\n\nSee `{PLAN}` for definitions and reading rules.\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"label": label, "out": str(args.out), "combined": combined["summary"]},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
