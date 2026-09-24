import csv
import json

from docs_transduction_study import coding_ai, rescore_a7


def make_attempt(coding, name, packet, answer, status):
    folder = coding / "m1_ai_attempts" / name
    folder.mkdir(parents=True)
    (folder / "packet.txt").write_text(json.dumps(packet))
    (folder / "result.json").write_text(
        json.dumps(
            {
                "status": status,
                "session_id": f"ses-{name}",
                "configuration": {"provider": "p", "model": "m"},
            }
        )
    )
    if answer is not None:
        (folder / "answer.json").write_text(json.dumps(answer))


def test_rescore_uses_latest_usable_attempt_and_keeps_strict(tmp_path):
    packet, key = coding_ai.prepare_packet(
        "S01-R1-001|explicit|A3",
        "Install before starting.",
        {"question": "Q?", "correct_answer": "Install first", "foil_1": "Start first"},
        "seed",
    )
    base = {
        "opaque_id": packet["opaque_id"],
        "option_id": key["correct_id"],
        "support": "explicit",
        "rationale": "",
    }
    opaque = packet["opaque_id"]
    make_attempt(tmp_path, f"{opaque}-p1-a1", packet, None, "export_failed")
    make_attempt(
        tmp_path,
        f"{opaque}-p1-a2",
        packet,
        {**base, "evidence": "install BEFORE starting"},
        "invalid_response",
    )
    make_attempt(
        tmp_path,
        f"{opaque}-p2-a1",
        packet,
        {**base, "evidence": "Install before starting."},
        "recorded",
    )
    summary = rescore_a7.rescore(tmp_path, {opaque: key})
    assert summary == {"rescored": 2, "still_invalid": 0}
    rows = {
        row["pass_number"]: row
        for row in csv.DictReader((tmp_path / "m1_ai_a7.csv").open())
    }
    assert (
        rows["1"]["score"] == "3"
        and rows["1"]["score_strict"] == ""
        and "verbatim" in rows["1"]["strict_error"]
    )
    assert rows["1"]["attempt"].endswith("-a2")
    assert rows["2"]["score"] == rows["2"]["score_strict"] == "3"
    records = list((tmp_path / rescore_a7.RECORDS_DIR).glob("*.json"))
    assert len(records) == 2 and all(
        json.loads(r.read_text())["isolation_verified"] for r in records
    )
    assert (
        rescore_a7.rescore(tmp_path, {opaque: key}) == summary
    )  # deterministic re-run
