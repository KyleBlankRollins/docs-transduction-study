from docs_transduction_study import exploratory


def record(arm, stage, score, flags=()):
    return {
        "assignment_id": f"S01-R1-001|{arm}|{stage}",
        "pass_number": 1,
        "score": score,
        "flags": list(flags),
    }


def test_correctness_and_support_breakdown():
    records = [
        record("explicit", "A1", 3),
        record("explicit", "A1", 2, ["explicit_quote_unverified"]),
        record("implicit", "A1", 3, ["quote_verified_after_normalization"]),
        record("implicit", "A1", 1),
        record("implicit", "A1", 2),
        {**record("implicit", "A1", 0), "pass_number": 2},
    ]
    tables = exploratory.diagnostics(records)
    gap = next(row for row in tables["correctness_gap"] if row["stage"] == "A1")
    assert gap["explicit_rate"] == 1.0 and gap["implicit_rate"] == 2 / 3
    support = {(r["stage"], r["arm"]): r for r in tables["support"]}
    assert support[("A1", "explicit")]["exact_quote"] == 1
    assert support[("A1", "explicit")]["unverified_quote"] == 1
    assert support[("A1", "implicit")]["normalized_quote"] == 1
    assert support[("A1", "implicit")]["inferred"] == 1
    assert support[("A4", "explicit")]["correct"] == 0
    assert support[("A4", "explicit")]["exact_quote_share"] is None
