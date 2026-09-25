import csv
import json

import pytest

from docs_transduction_study import analysis, coding_ai

SEED = "cd" * 32
INSTANCES = {
    "S01-R1-001": {"specimen_id": "S01", "relation_type": "R1", "demark_rule": "D1"},
    "S01-R3-001": {"specimen_id": "S01", "relation_type": "R3", "demark_rule": "D3"},
    "S02-O2-at-000100": {
        "specimen_id": "S02",
        "relation_type": "O2",
        "demark_rule": "",
    },
}
CONFIG = {"model": "synthetic"}


def assignments():
    return [
        f"{instance}|{arm}|{stage}"
        for instance in INSTANCES
        for arm in analysis.ARMS
        for stage in analysis.STAGES
    ]


def score_for(identifier):
    instance, arm, stage = identifier.split("|")
    if stage == "A4" and arm == "implicit":
        return 0 if instance.startswith("S01") else 1
    return 3 if arm == "explicit" else 2


def write_records(path, *, repeat_changes=0, isolation=True, configs=(CONFIG,), drop=0):
    records = path / coding_ai.RECORDS_DIR
    records.mkdir(parents=True)
    ids = assignments()
    opaque = {identifier: coding_ai.opaque_id(identifier, SEED) for identifier in ids}
    expected = [opaque[i] for i in ids]
    sample = set(coding_ai.repeat_sample(expected, SEED))
    written = 0
    for number, identifier in enumerate(ids[drop:]):
        for pass_number in (1, 2):
            if pass_number == 2 and opaque[identifier] not in sample:
                continue
            score = score_for(identifier)
            if pass_number == 2 and written < repeat_changes:
                score = (score + 1) % 4
                written += 1
            record = {
                "opaque_id": opaque[identifier],
                "assignment_id": identifier,
                "pass_number": pass_number,
                "score": score,
                "isolation_verified": isolation,
                "configuration": configs[number % len(configs)],
            }
            (records / f"{opaque[identifier]}-{pass_number}.json").write_text(
                json.dumps(record)
            )
    return expected


def run(tmp_path, **kwargs):
    expected = write_records(tmp_path / "coding", **kwargs)
    spans = {("S01-R1-001", "implicit"): True}
    return analysis.analyze(
        tmp_path / "coding", INSTANCES, expected, SEED, spans, tmp_path / "out"
    )


def read(path):
    with path.open() as handle:
        return list(csv.DictReader(handle))


def test_passing_gate_writes_prespecified_tables(tmp_path):
    report = run(tmp_path)
    assert (
        report["gate"]["substantive_findings_allowed"] and report["gate"]["kappa"] == 1
    )
    assert "Not M1a" in report["label"]
    gap = {row["stage"]: row for row in read(tmp_path / "out" / "h1_gap_pooled.csv")}
    assert float(gap["A1"]["gap"]) == 1.0
    assert set(read(tmp_path / "out" / "h1_pooled.csv")[0]) >= {
        "score_0",
        "score_1",
        "score_2",
        "score_3",
        "mean",
    }
    r3 = read(tmp_path / "out" / "r3_by_device.csv")
    assert {row["device"] for row in r3} == {"D3", "D4"}
    assert next(row for row in r3 if row["device"] == "D4")["n"] == "0"
    h3 = {
        (r["arm"], r["spans_chunks"]): r
        for r in read(tmp_path / "out" / "h3_by_arm_spans.csv")
    }
    assert h3[("implicit", "True")]["corrupted"] == "1"
    overall = read(tmp_path / "out" / "h3_overall.csv")[0]
    assert overall["corrupted"] == "2" and overall["absent"] == "1"
    observed = read(tmp_path / "out" / "h2_observed.csv")
    assert {row["relation"] for row in observed} == {"O2"}


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"drop": 1}, "missing"),
        ({"isolation": False}, "isolation"),
        ({"configs": (CONFIG, {"model": "other"})}, "configuration"),
        ({"repeat_changes": 3}, "kappa"),
    ],
)
def test_gate_failures_block_substantive_output(tmp_path, kwargs, reason):
    report = run(tmp_path, **kwargs)
    assert not report["gate"]["substantive_findings_allowed"]
    assert any(reason in failure for failure in report["gate"]["failures"])
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["report.json"]
    assert report["engineering"]["scores_withheld"]


def test_zero_denominators_and_missing_sides_are_explicit():
    rows = [
        {"stage": "A4", "arm": "explicit", "score": 0, "spans_chunks": False},
        {"stage": "A1", "arm": "explicit", "score": 3, "spans_chunks": None},
    ]
    assert analysis.corrupted_absent(rows, ())[0]["corrupted_to_absent"] is None
    table = analysis.survival_table(rows, ("stage", "arm"))
    assert analysis.gaps(table, ("stage",))[0]["gap"] is None
    assert analysis.survival_table([], ("stage", "arm")) == []


def test_constant_scores_leave_kappa_undefined(tmp_path):
    expected = write_records(tmp_path / "coding")
    records = analysis.load_records(tmp_path / "coding")
    for record in records:
        record["score"] = 3
    status = analysis.gate(records, expected, SEED)
    assert status["kappa"] is None and "kappa undefined" in status["failures"]


def test_a8_documented_unscorable_are_excused_and_others_fail(tmp_path):
    expected = write_records(tmp_path / "coding", drop=1)
    records = analysis.load_records(tmp_path / "coding")
    missing = sorted(
        set(expected) - {r["opaque_id"] for r in records if r["pass_number"] == 1}
    )
    assert len(missing) == 1
    blocked = analysis.gate(records, expected, SEED)
    assert not blocked["substantive_findings_allowed"]
    documented = {
        (missing[0], 1): "invalid under A7: Packet or response identity mismatch"
    }
    allowed = analysis.gate(records, expected, SEED, documented)
    assert allowed["substantive_findings_allowed"], allowed["failures"]
    assert allowed["coverage"] == f"{len(expected) - 1}/{len(expected)}"
    assert allowed["excused_first_pass"] == 1 and allowed["documented_unscorable"]
    sample = coding_ai.repeat_sample(expected, SEED)
    if missing[0] in sample:
        assert allowed["repeat_pairs_used"] == len(sample) - 1


def test_a8_unscorable_list_is_derived_from_evidence(tmp_path):
    coding = tmp_path / "coding"
    coding.mkdir()
    (coding / "m1_ai_a7_invalid.json").write_text(
        json.dumps(
            [
                {
                    "attempt": "AI-aaa-p1-a1",
                    "error": "Response fields do not match protocol",
                }
            ]
        )
    )
    ledger = [
        {"event": "result", "tag": "AI-bbb-p1", "status": "timeout"},
        {"event": "result", "tag": "AI-bbb-p1", "status": "timeout"},
        {"event": "result", "tag": "AI-ccc-p1", "status": "export_failed"},
        {"event": "result", "tag": "AI-ddd-p2", "status": "export_failed"},
        {"event": "result", "tag": "AI-ddd-p2", "status": "recorded"},
    ]
    (coding / "m1_ai_attempts.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in ledger)
    )
    documented = analysis.documented_unscorable(coding)
    assert set(documented) == {("AI-aaa", 1), ("AI-bbb", 1)}
    assert "2 attempt(s): timeout" in documented[("AI-bbb", 1)]
