import pytest

from docs_transduction_study import coding_ai


def packet_and_key():
    return coding_ai.prepare_packet(
        "PILOT-explicit-A3",
        "Install before starting.",
        {
            "question": "Which action comes first?",
            "correct_answer": "Installation precedes startup",
            "foil_1": "Startup precedes installation",
        },
        "pilot-seed",
    )


def response(
    packet,
    choice,
    support="explicit",
    evidence="Install before starting.",
    rationale="",
):
    return {
        "opaque_id": packet["opaque_id"],
        "option_id": choice,
        "support": support,
        "evidence": evidence,
        "rationale": rationale,
    }


def test_packet_separates_key_and_is_reproducible():
    packet, key = packet_and_key()
    assert (packet, key) == packet_and_key()
    assert (
        not {
            "assignment_id",
            "correct_id",
            "absent_id",
            "arm",
            "artifact_path",
            "correct_answer",
        }
        & packet.keys()
    )
    assert len(packet["options"]) == 3


def test_all_four_scores_and_malformed_responses():
    packet, key = packet_and_key()
    assert (
        coding_ai.score_response(packet, key, response(packet, key["correct_id"])) == 3
    )
    assert (
        coding_ai.score_response(
            packet,
            key,
            response(packet, key["correct_id"], "inferred", "", "Order inferred"),
        )
        == 2
    )
    assert (
        coding_ai.score_response(
            packet, key, response(packet, key["absent_id"], "absent", "")
        )
        == 1
    )
    foil = next(
        option["id"]
        for option in packet["options"]
        if option["id"] not in {key["correct_id"], key["absent_id"]}
    )
    assert coding_ai.score_response(packet, key, response(packet, foil)) == 0
    with pytest.raises(ValueError, match="verbatim"):
        coding_ai.score_response(
            packet, key, response(packet, key["correct_id"], evidence="Invented quote")
        )
    packet["artifact"] = "Changed"
    with pytest.raises(ValueError, match="mismatch"):
        coding_ai.score_response(packet, key, response(packet, key["correct_id"]))


def test_repeat_sample_and_fail_closed_repeatability():
    identifiers = [f"AI-{index}" for index in range(11)]
    sample = coding_ai.repeat_sample(identifiers, "seed")
    assert len(sample) == 3
    assert sample == coding_ai.repeat_sample(list(reversed(identifiers)), "seed")
    scores = dict.fromkeys(identifiers, 3)
    repeat_scores = dict(zip(sample, [0, 2, 3], strict=True))
    scores.update(repeat_scores)
    config = {"expected_ids": identifiers, "seed": "seed"}
    assert (
        coding_ai.repeatability(
            scores, repeat_scores, sample, **config, isolation_verified=True
        )["kappa"]
        == 1
    )
    constant = dict.fromkeys(identifiers, 3)
    assert not coding_ai.repeatability(
        constant, dict.fromkeys(sample, 3), sample, **config, isolation_verified=True
    )["substantive_findings_allowed"]
    with pytest.raises(ValueError, match="Isolated"):
        coding_ai.repeatability(
            scores, repeat_scores, sample, **config, isolation_verified=False
        )
    with pytest.raises(ValueError, match="locked sample"):
        coding_ai.repeatability(scores, {}, sample, **config, isolation_verified=True)
    with pytest.raises(ValueError, match="locked assignments"):
        coding_ai.repeatability(
            repeat_scores, repeat_scores, sample, **config, isolation_verified=True
        )


def test_records_are_append_only_and_sessions_are_fresh(tmp_path):
    packet, key = packet_and_key()
    answer = response(packet, key["correct_id"])
    provenance = {
        "evaluator": "disposable-test",
        "configuration": {"model": "test"},
        "isolation_verified": True,
    }
    coding_ai.record_response(
        tmp_path, packet, key, answer, pass_number=1, session_id="first", **provenance
    )
    original = (tmp_path / "m1_ai.csv").read_bytes()
    with pytest.raises(FileExistsError):
        coding_ai.record_response(
            tmp_path,
            packet,
            key,
            answer,
            pass_number=1,
            session_id="other",
            **provenance,
        )
    with pytest.raises(ValueError, match="fresh evaluator"):
        coding_ai.record_response(
            tmp_path,
            packet,
            key,
            answer,
            pass_number=2,
            session_id="first",
            **provenance,
        )
    assert (tmp_path / "m1_ai.csv").read_bytes() == original
    with pytest.raises(ValueError, match="original packet"):
        coding_ai.record_response(
            tmp_path,
            packet,
            key,
            answer,
            pass_number=2,
            session_id="changed",
            **{**provenance, "configuration": {"model": "different"}},
        )
    coding_ai.record_response(
        tmp_path, packet, key, answer, pass_number=2, session_id="second", **provenance
    )
    assert len(list((tmp_path / coding_ai.RECORDS_DIR).glob("*.json"))) == 2
    assert len((tmp_path / "m1_ai.csv").read_text().splitlines()) == 3


SNAPSHOT = """- paragraph:
  - text: You can set
  - code: "\\"baseUrl\\": x"
  - link "Model Context Protocol":
    - /url: https://example.com
  - text: is standard."""


@pytest.mark.parametrize(
    ("evidence", "artifact", "verified"),
    [
        (
            "Don't run npm build.",
            "<p>Don&#39;t run <code>npm</code>\n build.</p>",
            True,
        ),
        (
            'You can set "baseUrl": x Model Context Protocol is standard.',
            SNAPSHOT,
            True,
        ),
        (
            "Install before starting … start the server",
            "Install before starting. Then start the server.",
            True,
        ),
        (
            "start the server … Install before starting",
            "Install before starting. Then start the server.",
            False,
        ),
        ("Install … server", "Install before starting. Then start the server.", False),
        ("An invented sentence", "Install before starting.", False),
        ("- import the file", "- import the file today", True),
    ],
)
def test_a7_quote_verification(evidence, artifact, verified):
    assert coding_ai.quote_verified(evidence, artifact) is verified


def test_a7_scores_by_option_with_flags():
    packet, key = packet_and_key()
    exact = response(packet, key["correct_id"])
    assert coding_ai.score_response_a7(packet, key, exact) == (3, [])
    loose = response(packet, key["correct_id"], evidence="install  BEFORE starting")
    assert coding_ai.score_response_a7(packet, key, loose) == (
        3,
        ["quote_verified_after_normalization"],
    )
    unverified = response(packet, key["correct_id"], evidence="Invented quote")
    assert coding_ai.score_response_a7(packet, key, unverified) == (
        2,
        ["explicit_quote_unverified"],
    )
    with pytest.raises(ValueError, match="verbatim"):
        coding_ai.score_response(packet, key, unverified)
    absence = response(packet, key["absent_id"], "explicit", "Install before starting.")
    assert coding_ai.score_response_a7(packet, key, absence) == (
        1,
        ["absence_with_support_or_quote"],
    )
    foil = next(
        o["id"]
        for o in packet["options"]
        if o["id"] not in {key["correct_id"], key["absent_id"]}
    )
    assert (
        coding_ai.score_response_a7(
            packet, key, response(packet, foil, evidence="nope")
        )[0]
        == 0
    )
    with pytest.raises(ValueError, match="identity"):
        coding_ai.score_response_a7(packet, key, {**exact, "opaque_id": "AI-other"})
