from docs_transduction_study import analysis, replication, rescore_a7


def sides(ref_mean, rep_mean):
    def make(mean):
        return {
            "blocked": False,
            "mean_gap": dict(zip(replication.STAGES, mean)),
            "correctness_gap": dict(zip(replication.STAGES, [0.0, -0.01, 0.0, 0.02])),
        }

    return make(ref_mean), make(rep_mean)


def test_sign_agreement_per_stage_and_measure():
    ref, rep = sides([-0.1, -0.1, -0.1, -0.1], [-0.2, 0.1, 0.0, -0.05])
    rows = replication.compare(ref, rep)["rows"]
    mean = [r["signs_agree"] for r in rows if r["measure"] == "mean_gap"]
    assert mean == [True, False, False, True]
    assert len(rows) == 8


def test_blocked_side_is_not_compared():
    ref, _ = sides([-0.1] * 4, [-0.1] * 4)
    result = replication.compare(ref, {"blocked": True})
    assert result["replication_blocked"] and result["rows"] == []


def test_evaluator_label_keeps_opencode_and_names_batch_transport():
    glm = {
        "transport": "opencode-runner-1",
        "provider": "opencode-go",
        "model": "glm-5.3-flash",
    }
    claude = {
        "transport": "anthropic-batch-runner-1",
        "provider": "anthropic",
        "model": "claude-sonnet-5-5",
    }
    assert rescore_a7.evaluator_label(glm) == "opencode:opencode-go/glm-5.3-flash"
    assert rescore_a7.evaluator_label(claude) == "anthropic-batch:claude-sonnet-5-5"


def test_refusal_is_documented_unscorable_after_one_attempt(tmp_path):
    (tmp_path / "m1_ai_attempts.jsonl").write_text(
        '{"event": "invoke", "tag": "AI-x-p1", "attempt": 1}\n'
        '{"event": "result", "tag": "AI-x-p1", "status": "refusal", "detail": "cyber"}\n'
    )
    documented = analysis.documented_unscorable(tmp_path)
    assert documented == {("AI-x", 1): "no usable answer after 1 attempt(s): refusal"}
