"""Closed-book covariate (A11): packets, scoring, runner path, analysis."""

import json
from types import SimpleNamespace as NS

import pytest
from test_batch_runner import CONFIG as OPEN_CONFIG
from test_batch_runner import FakeClient, message, packet_and_key

from docs_transduction_study import batch_runner as br
from docs_transduction_study import closed_book as cb
from docs_transduction_study import coding_ai
from docs_transduction_study import exploratory_plan as ep
from docs_transduction_study import opencode_runner as orr
from docs_transduction_study.opencode_runner import RunnerError

CB_CONFIG = br.BatchConfig(protocol=cb.CB_PROTOCOL)


def cb_pair(name="A"):
    packet, key = packet_and_key(name)
    return cb.closed_book_packet(packet, key, "synthetic-seed")


def answer(packet, option, support="inferred", evidence=""):
    return {
        "opaque_id": packet["opaque_id"],
        "option_id": option,
        "support": support,
        "evidence": evidence,
        "rationale": "From memory.",
    }


def test_packet_drops_the_artifact_and_keeps_options():
    packet, key = packet_and_key("A")
    cbp, cbk = cb.closed_book_packet(packet, key, "synthetic-seed")
    assert "artifact" not in cbp
    assert cbp["options"] == packet["options"] and cbp["question"] == packet["question"]
    assert cbp["instruction"] == cb.CB_INSTRUCTION and cbp["protocol"] == cb.CB_PROTOCOL
    assert cbp["opaque_id"] != packet["opaque_id"]
    assert (cbk["correct_id"], cbk["absent_id"]) == (
        key["correct_id"],
        key["absent_id"],
    )
    assert cbk["source_opaque_id"] == packet["opaque_id"]


def test_packet_refuses_a_mismatched_key():
    packet, key = packet_and_key("A")
    with pytest.raises(ValueError, match="does not match"):
        cb.closed_book_packet({**packet, "question": "changed"}, key, "seed")


def test_scoring_by_option_with_flags():
    packet, key = cb_pair()
    foil = next(
        o["id"]
        for o in packet["options"]
        if o["id"] not in (key["correct_id"], key["absent_id"])
    )
    assert cb.score_closed_book(packet, key, answer(packet, key["correct_id"])) == (
        "cb_correct",
        [],
    )
    assert cb.score_closed_book(packet, key, answer(packet, foil))[0] == "cb_foil"
    outcome, flags = cb.score_closed_book(
        packet, key, answer(packet, key["absent_id"], support="inferred")
    )
    assert outcome == "cb_declined" and flags == ["declined_without_absent_support"]
    _, flags = cb.score_closed_book(
        packet, key, answer(packet, key["correct_id"], "explicit", "quote")
    )
    assert flags == ["evidence_not_empty", "support_not_inferred"]
    with pytest.raises(ValueError, match="Unknown option"):
        cb.score_closed_book(packet, key, answer(packet, "9"))
    with pytest.raises(ValueError, match="fields"):
        cb.score_closed_book(packet, key, {"opaque_id": packet["opaque_id"]})


def test_record_is_append_only_and_separate(tmp_path):
    packet, key = cb_pair()
    kwargs = {
        "pass_number": 1,
        "session_id": "s1",
        "evaluator": "e",
        "configuration": {"x": 1},
        "isolation_verified": True,
    }
    out = cb.record_closed_book(
        tmp_path, packet, key, answer(packet, key["correct_id"]), **kwargs
    )
    assert out["score"] == "cb_correct"
    assert (tmp_path / cb.RECORDS_DIR).exists()
    assert not (tmp_path / coding_ai.RECORDS_DIR).exists()
    with pytest.raises(ValueError, match="fresh"):
        cb.record_closed_book(
            tmp_path, packet, key, answer(packet, key["correct_id"]), **kwargs
        )
    assert cb.recorder_for(cb.CB_PROTOCOL)[1] == cb.RECORDS_DIR
    assert cb.recorder_for(coding_ai.PROTOCOL_VERSION)[1] == coding_ai.RECORDS_DIR


def test_open_book_configurations_are_unchanged():
    config = br.configuration_record(OPEN_CONFIG)
    assert config["protocol"] == coding_ai.PROTOCOL_VERSION
    assert config["evaluator_prompt_sha256"] == cb.instruction_sha(
        coding_ai.PROTOCOL_VERSION
    )
    closed = br.configuration_record(CB_CONFIG)
    assert closed["protocol"] == cb.CB_PROTOCOL and closed != config


def test_batch_runner_closed_book_path(tmp_path):
    pairs = [cb_pair("A"), cb_pair("B")]

    def reply(custom_id, params):
        packet, key = next(p for p in pairs if custom_id.startswith(p[0]["opaque_id"]))
        assert "artifact" not in json.loads(params["messages"][0]["content"])
        return NS(
            type="succeeded",
            message=message(json.dumps(answer(packet, key["correct_id"]))),
        )

    client = FakeClient(reply)
    coding = tmp_path / "cb"
    br.submit(
        client,
        [p for p, _ in pairs],
        pass_number=1,
        coding=coding,
        config=CB_CONFIG,
        max_invocations=5,
    )
    keys = {p["opaque_id"]: k for p, k in pairs}
    assert br.collect(client, keys, coding=coding, config=CB_CONFIG)["counts"] == {
        "recorded": 2
    }
    assert len(list((coding / cb.RECORDS_DIR).glob("*.json"))) == 2
    assert set(cb.load_outcomes(coding).values()) == {"cb_correct"}


def test_runners_refuse_protocol_mismatch(tmp_path):
    packet, key = packet_and_key("A")
    (tmp_path / "packet.txt").write_text(json.dumps(packet))
    with pytest.raises(RunnerError, match="protocol"):
        br._record_item(
            NS(result=NS(type="succeeded", message=message("{}"))),
            tmp_path,
            key,
            pass_number=1,
            coding=tmp_path,
            config=CB_CONFIG,
        )
    with (
        orr.Ledger(tmp_path, 5) as ledger,
        pytest.raises(RunnerError, match="protocol"),
    ):
        orr.run_assignment(
            packet,
            key,
            pass_number=1,
            output=tmp_path,
            ledger=ledger,
            config=orr.RunnerConfig(binary="opencode", protocol=cb.CB_PROTOCOL),
            isolation={"cli_version": "x"},
        )


# ── Analysis on synthetic rows ─────────────────────────────────────────────


def rows_and_outcomes():
    instances = {
        "S01-R1-1": {"relation_type": "R1", "specimen_id": "S01"},
        "S02-O1-1": {"relation_type": "O1", "specimen_id": "S02"},
    }
    rows, outcomes = [], {}
    for i, inst in instances.items():
        for arm in ep.ARMS:
            for stage in ep.STAGES:
                score = 3 if arm == "implicit" else (1 if stage == "A4" else 2)
                rows.append(
                    {
                        "instance_id": i,
                        "specimen_id": inst["specimen_id"],
                        "relation": inst["relation_type"],
                        "arm": arm,
                        "stage": stage,
                        "score": score,
                        "spans_chunks": None,
                        "opaque_id": f"{i}{arm}{stage}",
                    }
                )
                # R1 known (8/8 correct); O1 unknown (4/8 correct).
                known = i == "S01-R1-1" or arm == "explicit"
                outcomes[f"{i}|{arm}|{stage}"] = (
                    "cb_correct" if known else "cb_declined"
                )
    return instances, rows, outcomes


def test_known_threshold_and_accuracy():
    instances, _, outcomes = rows_and_outcomes()
    known = {k["instance_id"]: k for k in cb.known_instances(outcomes, instances)}
    assert known["S01-R1-1"]["known"] and known["S01-R1-1"]["cb_correct"] == 8
    assert not known["S02-O1-1"]["known"] and known["S02-O1-1"]["cb_correct"] == 4
    overall = cb.accuracy(list(known.values()))[0]
    assert overall["answers"] == 16 and overall["cb_correct_rate"] == pytest.approx(
        12 / 16
    )


def test_crosstab_categories():
    _, rows, outcomes = rows_and_outcomes()
    table = {(r["stage"], r["arm"]): r for r in cb.crosstab(rows, outcomes)}
    a4_explicit = table[("A4", "explicit")]
    assert a4_explicit["lost_despite_knowledge"] == 2
    a1_implicit = table[("A1", "implicit")]
    assert (
        a1_implicit["known_both_correct"] == 1
        and a1_implicit["recovered_from_artifact"] == 1
    )


def test_unknown_gaps_and_familiarity():
    instances, rows, outcomes = rows_and_outcomes()
    boot = ep.Bootstrap(["S01", "S02"], 200, "t")
    known = cb.known_instances(outcomes, instances)
    gaps = cb.unknown_gaps(rows, known, boot)
    assert gaps["unknown_instances"] == [{"n": 1, "complete_pairs": 4}]
    assert {r["outcome"] for r in gaps["e1"]} == {"correct", "quotable_conditional"}
    fam = {r["stage"]: r for r in cb.familiarity(rows, outcomes, boot)}
    # At A4 the explicit arm is lost (score 1) while closed-book is correct: +1 for both.
    assert fam["A4"]["point"] == pytest.approx(1.0)
    assert fam["A1"]["point"] == pytest.approx(0.0)
    robust = cb.single_evaluator_robustness(gaps)
    assert all("robust_specimen_criterion_only" in r for r in robust)
