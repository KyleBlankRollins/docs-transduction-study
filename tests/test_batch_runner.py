import itertools
import json
from types import SimpleNamespace as NS

import pytest

from docs_transduction_study import batch_runner as br
from docs_transduction_study import coding_ai, rescore_a7
from docs_transduction_study.opencode_runner import RunnerError

CONFIG = br.BatchConfig()
IDS = itertools.count()


def packet_and_key(name):
    return coding_ai.prepare_packet(
        name,
        'Install "first".\nThen start.',
        {
            "question": "Which action comes first?",
            "correct_answer": "Installation precedes startup",
            "foil_1": "Startup precedes installation",
        },
        "synthetic-seed",
    )


def correct_answer(packet, key):
    return {
        "opaque_id": packet["opaque_id"],
        "option_id": key["correct_id"],
        "support": "explicit",
        "evidence": 'Install "first".',
        "rationale": "",
    }


class Dumpable(NS):
    def model_dump(self, mode="json"):
        def dump(v):
            if isinstance(v, NS):
                return {k: dump(x) for k, x in vars(v).items()}
            if isinstance(v, list):
                return [dump(x) for x in v]
            return v

        return dump(self)


def message(text, *, model=CONFIG.model, stop="end_turn", extra_blocks=()):
    blocks = [
        NS(type="thinking", thinking=""),
        *extra_blocks,
        NS(type="text", text=text),
    ]
    return Dumpable(
        id=f"msg_{next(IDS)}",
        model=model,
        stop_reason=stop,
        content=blocks,
        usage=Dumpable(input_tokens=100, output_tokens=20),
    )


class FakeClient:
    """In-memory stand-in for client.messages.batches (no network)."""

    def __init__(self, reply):
        self.reply = reply  # custom_id, params -> result namespace
        self.created = []
        self.status = "ended"
        batches = NS(
            create=self._create, retrieve=self._retrieve, results=self._results
        )
        self.messages = NS(batches=batches, count_tokens=self._count)

    def _create(self, requests):
        self.created.append(requests)
        return NS(id=f"msgbatch_{len(self.created)}")

    def _retrieve(self, batch_id):
        return NS(processing_status=self.status)

    def _results(self, batch_id):
        requests = self.created[int(batch_id.split("_")[1]) - 1]
        return [
            NS(custom_id=r["custom_id"], result=self.reply(r["custom_id"], r["params"]))
            for r in requests
        ]

    def _count(self, model, system, messages):
        return NS(input_tokens=len(messages[0]["content"]))


def succeed(packets_keys):
    by_id = {p["opaque_id"]: (p, k) for p, k in packets_keys}

    def reply(custom_id, params):
        packet, key = by_id[custom_id.rsplit("-", 2)[0]]
        return NS(
            type="succeeded", message=message(json.dumps(correct_answer(packet, key)))
        )

    return reply


def test_request_is_the_runner_prompt_and_packet_verbatim():
    packet, _ = packet_and_key("A")
    params = br.request_params(packet, CONFIG)
    assert params["system"] == br.AGENT_PROMPT
    assert params["messages"] == [{"role": "user", "content": br.packet_text(packet)}]
    assert "tools" not in params and "temperature" not in params
    assert "fallbacks" not in params


def test_submit_then_collect_records_scores(tmp_path):
    pairs = [packet_and_key("A"), packet_and_key("B")]
    client = FakeClient(succeed(pairs))
    coding = tmp_path / "coding-sonnet"
    out = br.submit(
        client,
        [p for p, _ in pairs],
        pass_number=1,
        coding=coding,
        config=CONFIG,
        max_invocations=10,
    )
    assert out["batches"] == [{"batch_id": "msgbatch_1", "requests": 2}]
    keys = {p["opaque_id"]: k for p, k in pairs}
    result = br.collect(client, keys, coding=coding, config=CONFIG)
    assert result == {"counts": {"recorded": 2}, "waiting": []}
    records = list((coding / coding_ai.RECORDS_DIR).glob("*.json"))
    assert len(records) == 2
    assert {json.loads(r.read_text())["score"] for r in records} == {3}
    # Re-running collect and submit is idempotent.
    assert br.collect(client, keys, coding=coding, config=CONFIG)["counts"] == {}
    again = br.submit(
        client,
        [p for p, _ in pairs],
        pass_number=1,
        coding=coding,
        config=CONFIG,
        max_invocations=10,
    )
    assert again["batches"] == [] and again["skipped"] == 2
    # The A7 rescorer reads this layout unchanged.
    scored = rescore_a7.latest_answers(coding)
    assert set(scored) == {(p["opaque_id"], 1) for p, _ in pairs}


def test_repeat_pass_matches_first_pass_configuration(tmp_path):
    pairs = [packet_and_key("A")]
    client = FakeClient(succeed(pairs))
    coding = tmp_path / "c"
    keys = {p["opaque_id"]: k for p, k in pairs}
    for pass_number in (1, 2):
        br.submit(
            client,
            [pairs[0][0]],
            pass_number=pass_number,
            coding=coding,
            config=CONFIG,
            max_invocations=10,
        )
        assert br.collect(client, keys, coding=coding, config=CONFIG)["counts"] == {
            "recorded": 1
        }


def test_budget_is_checked_before_any_batch(tmp_path):
    pairs = [packet_and_key("A"), packet_and_key("B")]
    client = FakeClient(succeed(pairs))
    with pytest.raises(RunnerError, match="budget"):
        br.submit(
            client,
            [p for p, _ in pairs],
            pass_number=1,
            coding=tmp_path / "c",
            config=CONFIG,
            max_invocations=1,
        )
    assert client.created == []


def test_transport_failures_retry_once_and_final_outcomes_do_not(tmp_path):
    pairs = [packet_and_key("A"), packet_and_key("B")]
    outcomes = {
        pairs[0][0]["opaque_id"]: NS(type="expired"),
        pairs[1][0]["opaque_id"]: NS(type="succeeded", message=message("not json")),
    }
    client = FakeClient(lambda cid, _: outcomes[cid.rsplit("-", 2)[0]])
    coding = tmp_path / "c"
    keys = {p["opaque_id"]: k for p, k in pairs}
    packets = [p for p, _ in pairs]
    br.submit(
        client, packets, pass_number=1, coding=coding, config=CONFIG, max_invocations=10
    )
    counts = br.collect(client, keys, coding=coding, config=CONFIG)["counts"]
    assert counts == {"expired": 1, "malformed_json": 1}
    second = br.submit(
        client, packets, pass_number=1, coding=coding, config=CONFIG, max_invocations=10
    )
    assert second["batches"] == [{"batch_id": "msgbatch_2", "requests": 1}]
    br.collect(client, keys, coding=coding, config=CONFIG)
    third = br.submit(
        client, packets, pass_number=1, coding=coding, config=CONFIG, max_invocations=10
    )
    assert third["batches"] == []  # attempts exhausted / retained failure


@pytest.mark.parametrize(
    "msg, problem",
    [
        (message("{}", model="claude-opus-5-5"), "wrong_response_model"),
        (message("{}", stop="max_tokens"), "stop_reason:max_tokens"),
        (
            message("{}", extra_blocks=[NS(type="tool_use")]),
            "unexpected_block:tool_use",
        ),
    ],
)
def test_output_checks(msg, problem):
    problems, _ = br.check_message(msg, CONFIG)
    assert problem in problems


def test_pending_batches_are_left_for_later(tmp_path):
    pairs = [packet_and_key("A")]
    client = FakeClient(succeed(pairs))
    coding = tmp_path / "c"
    br.submit(
        client,
        [pairs[0][0]],
        pass_number=1,
        coding=coding,
        config=CONFIG,
        max_invocations=10,
    )
    client.status = "in_progress"
    keys = {p["opaque_id"]: k for p, k in pairs}
    assert br.collect(client, keys, coding=coding, config=CONFIG) == {
        "counts": {},
        "waiting": ["msgbatch_1"],
    }
    # In-flight assignments are not resubmitted.
    again = br.submit(
        client,
        [pairs[0][0]],
        pass_number=1,
        coding=coding,
        config=CONFIG,
        max_invocations=10,
    )
    assert again["batches"] == []


def test_unconfirmed_submission_blocks_resubmission(tmp_path):
    pairs = [packet_and_key("A")]
    client = FakeClient(succeed(pairs))

    def crash(requests):
        raise ConnectionError("lost")

    client.messages.batches.create = crash
    coding = tmp_path / "c"
    with pytest.raises(ConnectionError):
        br.submit(
            client,
            [pairs[0][0]],
            pass_number=1,
            coding=coding,
            config=CONFIG,
            max_invocations=10,
        )
    with pytest.raises(RunnerError, match="Unconfirmed"):
        br.submit(
            client,
            [pairs[0][0]],
            pass_number=1,
            coding=coding,
            config=CONFIG,
            max_invocations=10,
        )


def test_refuses_the_glm_coding_directory():
    with pytest.raises(RunnerError, match="separate"):
        br.submit(
            FakeClient(None),
            [],
            pass_number=1,
            coding=br.REPO_ROOT / "coding",
            config=CONFIG,
            max_invocations=1,
        )


def test_chunking_respects_byte_limit(monkeypatch):
    monkeypatch.setattr(br, "MAX_BATCH_BYTES", 300)
    requests = [{"custom_id": str(i), "params": {"x": "y" * 100}} for i in range(5)]
    parts = br.chunk(requests)
    assert sum(len(p) for p in parts) == 5 and len(parts) > 1


def test_estimate_prices_input_and_assumed_output():
    packet, _ = packet_and_key("A")
    client = FakeClient(None)
    out = br.estimate(client, [packet], CONFIG, output_tokens_per_request=1000)
    assert out["input_tokens"] == len(br.packet_text(packet))
    assert out["assumed_output_tokens"] == 1000


@pytest.mark.parametrize(
    "kind, status",
    [("overloaded_error", "api_error"), ("invalid_request_error", "request_rejected")],
)
def test_errored_results_split_transient_from_final(tmp_path, kind, status):
    pairs = [packet_and_key("A")]
    error = NS(type="error", error=NS(type=kind))
    client = FakeClient(lambda cid, _: NS(type="errored", error=error))
    coding = tmp_path / "c"
    br.submit(
        client,
        [pairs[0][0]],
        pass_number=1,
        coding=coding,
        config=CONFIG,
        max_invocations=10,
    )
    keys = {p["opaque_id"]: k for p, k in pairs}
    assert br.collect(client, keys, coding=coding, config=CONFIG)["counts"] == {
        status: 1
    }


def test_refusal_is_recorded_as_final(tmp_path):
    pairs = [packet_and_key("A")]
    refused = message("", stop="refusal")
    refused.content = []
    refused.stop_details = NS(category="cyber")
    client = FakeClient(lambda cid, _: NS(type="succeeded", message=refused))
    coding = tmp_path / "c"
    packets = [pairs[0][0]]
    keys = {p["opaque_id"]: k for p, k in pairs}
    br.submit(
        client, packets, pass_number=1, coding=coding, config=CONFIG, max_invocations=10
    )
    assert br.collect(client, keys, coding=coding, config=CONFIG)["counts"] == {
        "refusal": 1
    }
    again = br.submit(
        client, packets, pass_number=1, coding=coding, config=CONFIG, max_invocations=10
    )
    assert again["batches"] == []
