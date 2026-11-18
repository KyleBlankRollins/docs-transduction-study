"""Synthetic-data tests for the E1-E7 exploratory analyses (no study data)."""

import pytest

from docs_transduction_study import exploratory_plan as ep

STAGES = ep.STAGES


def row(instance, specimen, relation, arm, stage, score, spans=None):
    return {
        "instance_id": instance,
        "specimen_id": specimen,
        "relation": relation,
        "arm": arm,
        "stage": stage,
        "score": score,
        "spans_chunks": spans if stage == "A4" else None,
        "opaque_id": f"AI-{instance}-{arm}-{stage}",
    }


def instance_rows(instance, specimen, relation, explicit, implicit):
    """explicit/implicit: four scores for A1-A4."""
    out = []
    for stage, e, i in zip(STAGES, explicit, implicit, strict=True):
        out.append(row(instance, specimen, relation, "explicit", stage, e, False))
        out.append(row(instance, specimen, relation, "implicit", stage, i, True))
    return out


@pytest.fixture
def rows():
    data = []
    data += instance_rows("S01-R1-1", "S01", "R1", [3, 3, 2, 2], [3, 3, 3, 3])
    data += instance_rows("S01-O1-1", "S01", "O1", [3, 2, 2, 1], [3, 3, 2, 1])
    data += instance_rows("S02-R2-1", "S02", "R2", [2, 2, 2, 0], [3, 3, 3, 1])
    data += instance_rows("S02-O2-1", "S02", "O2", [3, 3, 3, 3], [3, 3, 3, 3])
    data += instance_rows("S03-R3-1", "S03", "R3", [3, 3, 3, 3], [2, 2, 2, 2])
    data += instance_rows("S03-O1-2", "S03", "O1", [2, 2, 2, 2], [3, 3, 3, 3])
    return data


@pytest.fixture
def boot():
    return ep.Bootstrap(["S01", "S02", "S03"], 500, "test-seed")


def test_pairs_are_complete_and_incomplete_ones_are_listed(rows):
    rows = [
        r
        for r in rows
        if not (
            r["instance_id"] == "S01-R1-1"
            and r["arm"] == "implicit"
            and r["stage"] == "A2"
        )
    ]
    pairs, incomplete = ep.make_pairs(rows)
    assert len(pairs) == 6 * 4 - 1
    assert incomplete == [
        {"instance_id": "S01-R1-1", "stage": "A2", "missing": "implicit"}
    ]
    assert {p["group"] for p in pairs} == {"manipulated", "observed"}


def test_boundary_gaps_sum_to_the_score_gap(rows, boot):
    pairs, _ = ep.make_pairs(rows)
    for stage in STAGES:
        here = [p for p in pairs if p["stage"] == stage]
        total = boot.summarize(ep.paired_gap(here, lambda s: s))["point"]
        parts = sum(
            boot.summarize(ep.paired_gap(here, fn))["point"]
            for fn in ep.BOUNDARIES.values()
        )
        assert parts == pytest.approx(total)


def test_difference_in_differences_point_and_signs(rows, boot):
    pairs, _ = ep.make_pairs([r for r in rows if r["stage"] == "A1"])
    manipulated = ep.paired_gap(
        [p for p in pairs if p["group"] == "manipulated"], lambda s: s
    )
    observed = ep.paired_gap(
        [p for p in pairs if p["group"] == "observed"], lambda s: s
    )
    g_r = boot.summarize(manipulated)["point"]
    g_o = boot.summarize(observed)["point"]
    did = boot.summarize(ep.difference_in_differences(manipulated, observed))
    # A1 gaps: R1 0, R2 -1, R3 +1 -> 0; O1 0, O2 0, O1 -1 -> -1/3.
    assert g_r == pytest.approx(0.0)
    assert g_o == pytest.approx(-1 / 3)
    assert did["point"] == pytest.approx(1 / 3)
    assert did["ci_low"] <= did["point"] <= did["ci_high"]
    assert (
        did["specimens_negative"] + did["specimens_zero"] + did["specimens_positive"]
        == 3
    )


def test_bootstrap_is_deterministic_for_a_seed(rows):
    pairs, _ = ep.make_pairs(rows)
    stat = ep.paired_gap(pairs, lambda s: s)
    a = ep.Bootstrap(["S01", "S02", "S03"], 300, "same").summarize(stat)
    b = ep.Bootstrap(["S01", "S02", "S03"], 300, "same").summarize(stat)
    assert a == b


def test_specimen_without_data_is_counted(boot):
    pairs = [{"specimen_id": "S01", "explicit": 3, "implicit": 2}]
    summary = boot.summarize(ep.paired_gap(pairs, lambda s: s))
    assert summary["specimens_without_data"] == 2
    assert summary["specimens_positive"] == 1


def test_quotable_conditional_uses_pairs_correct_in_both_arms(boot):
    pairs = [
        {"specimen_id": "S01", "explicit": 2, "implicit": 3},  # both correct: -1
        {"specimen_id": "S01", "explicit": 0, "implicit": 3},  # excluded
    ]
    assert boot.summarize(ep.quotable_conditional(pairs))["point"] == pytest.approx(
        -1.0
    )
    uncond = boot.summarize(ep.quotable_unconditional(pairs))["point"]
    assert uncond == pytest.approx(0 / 1 - 2 / 2)


def test_kappa_values():
    assert ep.kappa([(0, 0), (1, 1), (2, 2), (3, 3)], ep.SCORES) == pytest.approx(1.0)
    assert ep.kappa([(3, 3), (3, 3)], ep.SCORES) is None
    assert ep.kappa([], ep.SCORES) is None


def test_e5_first_loss_and_widening(rows, boot):
    pairs, _ = ep.make_pairs(rows)
    out = ep.e5(rows, pairs, boot)
    loss = {
        (r["arm"], r["threshold"], r["first_stage"]): r["n"] for r in out["first_loss"]
    }
    # Explicit below 3: S01-R1 A3, S01-O1 A2, S02-R2 A1, S03-O1 A1; never for two.
    assert loss[("explicit", "below_3", "A1")] == 2
    assert loss[("explicit", "below_3", "never")] == 2
    assert loss[("explicit", "at_most_1", "A4")] == 2
    mean = next(r for r in out["widening"] if r["change"] == "mean")
    # Changes A1->A4: R1 -1, O1 0, R2 0, O2 0, R3 0, O1 0.
    assert mean["n"] == 6
    assert mean["point"] == pytest.approx(-1 / 6)
    transitions = [
        r
        for r in out["transitions"]
        if r["arm"] == "implicit" and r["from_stage"] == "A3"
    ]
    assert sum(r["n"] for r in transitions) == 6


def test_e6_spans_split_at_a4(rows, boot):
    pairs, _ = ep.make_pairs(rows)
    spans = ep.e6(rows, pairs, boot)["spans"]
    implicit_split = next(
        r for r in spans if r["arm"] == "implicit" and r["spans_chunks"] is True
    )
    assert implicit_split["n"] == 6 and implicit_split["absent"] == 2
    gaps = ep.e6(rows, pairs, boot)["gaps"]
    assert {g["relation"] for g in gaps} == set(ep.RELATIONS)
    assert all(g["too_small"] == (g["relation"] == "R4") for g in gaps)


def test_e4_agreement_and_agreed_subset(rows, boot):
    other = [dict(r) for r in rows]
    other[0]["score"] = 0  # one disagreement
    out = ep.e4({"a": rows, "b": other}, boot)
    assert out["summary"]["shared_assignments"] == len(rows)
    assert out["summary"]["agreed_assignments"] == len(rows) - 1
    assert out["summary"]["agreed_complete_pairs"] == 6 * 4 - 1
    assert sum(r["n"] for r in out["confusion"]) == len(rows)


def test_robustness_rule():
    def table(point, negative):
        return {
            "e1": [
                {
                    "stage": "A1",
                    "outcome": "score",
                    "quantity": "DiD",
                    "point": point,
                    "specimens_negative": negative,
                    "specimens_positive": 12 - negative,
                }
            ],
            "e2_gaps": [],
            "e6_gaps": [],
        }

    robust = ep.robustness({"a": table(-0.1, 9), "b": table(-0.2, 8)})
    assert robust[0]["same_sign"] and robust[0]["robust"]
    weak = ep.robustness({"a": table(-0.1, 9), "b": table(-0.2, 7)})
    assert weak[0]["same_sign"] and not weak[0]["robust"]
    split = ep.robustness({"a": table(-0.1, 9), "b": table(0.2, 3)})
    assert not split[0]["same_sign"] and not split[0]["robust"]


def test_e7_takes_all_corrupted_and_a_stable_absent_sample(rows):
    many = rows + [
        row(f"S01-O1-x{i}", "S01", "O1", "explicit", "A4", 1) for i in range(30)
    ]
    cases = ep.e7({"a": many})
    assert sum(c["reason"] == "corrupted" for c in cases) == 1
    assert sum(c["reason"] == "absent_sample" for c in cases) == ep.ABSENT_SAMPLE
    assert cases == ep.e7({"a": list(reversed(many))})
    assert all(c["category"] == "" for c in cases)


def test_plan_commit_is_found():
    sha = ep.plan_commit()
    assert len(sha) == 40
