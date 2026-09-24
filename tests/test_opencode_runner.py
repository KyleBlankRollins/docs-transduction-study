import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from docs_transduction_study import coding_ai
from docs_transduction_study import opencode_runner as runner

CONFIG = runner.RunnerConfig(binary="opencode")


def packet_and_key(name="SYNTH-1"):
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


class FakeCLI:
    """Scripted stand-in for the OpenCode binary."""

    def __init__(self, answer=None, **overrides):
        self.answer = answer
        self.overrides = overrides
        self.calls = []
        self.sessions = 0
        self.last_session = None
        self.last_input = None

    def __call__(self, args, *, input, cwd, env, timeout):
        self.calls.append({"args": args, "cwd": cwd, "env": env, "input": input})
        assert not Path(cwd).resolve().is_relative_to(runner.REPO_ROOT)
        command = args[1:]

        def done(stdout="", code=0, stderr=""):
            return subprocess.CompletedProcess(args, code, stdout, stderr)

        if command == ["--version"]:
            return done(self.overrides.get("version", "1.18.32") + "\n")
        if command == ["debug", "config"]:
            config = runner.opencode_config(CONFIG)
            config.update(self.overrides.get("config", {}))
            return done(json.dumps(config))
        if command == ["debug", "skill"]:
            skills = self.overrides.get(
                "skills", [{"name": "customize-opencode", "location": "<built-in>"}]
            )
            return done(json.dumps(skills))
        if command[:2] == ["debug", "agent"]:
            return done(
                json.dumps(
                    {
                        "prompt": runner.AGENT_PROMPT,
                        "tools": self.overrides.get(
                            "tools", {"read": False, "bash": False}
                        ),
                        "permission": [
                            {"permission": "*", "action": "deny", "pattern": "*"}
                        ],
                    }
                )
            )
        if command[:2] == ["session", "list"]:
            return done(self.overrides.get("history", ""))
        if command[0] == "run":
            if self.overrides.get("timeout"):
                raise subprocess.TimeoutExpired(args, timeout)
            self.sessions += 1
            self.last_session = f"ses_{self.sessions}"
            self.last_input = input
            return done(
                self.overrides.get("events") or self.events(self.last_session),
                self.overrides.get("exit", 0),
            )
        if command[0] == "export":
            return done(json.dumps(self.export(command[1])))
        raise AssertionError(command)

    def events(self, session):
        def line(kind, **part):
            return json.dumps(
                {"type": kind, "timestamp": 1, "sessionID": session, "part": part}
            )

        rows = [line("step_start", type="step-start")]
        rows += self.overrides.get("extra_events", [])
        rows.append(
            line("text", type="text", text=self.answer, time={"start": 1, "end": 2})
        )
        tokens = {
            "input": 10,
            "output": 5,
            "reasoning": 0,
            "cache": {"read": 0, "write": 0},
        }
        reason = self.overrides.get("reason", "stop")
        rows.append(
            line(
                "step_finish", type="step-finish", reason=reason, tokens=tokens, cost=0
            )
        )
        return "\n".join(rows) + "\n"

    def export(self, session):
        model = self.overrides.get("model", ("opencode-go", "glm-5.3-flash"))
        user = {
            "info": {"role": "user", "id": "m1", "sessionID": session},
            "parts": [{"type": "text", "text": self.last_input}],
        }
        assistant = {
            "info": {
                "role": "assistant",
                "mode": "evaluator",
                "providerID": model[0],
                "modelID": model[1],
                "sessionID": session,
            },
            "parts": [
                {"type": "step-start"},
                {"type": "text", "text": self.answer},
                {"type": "step-finish"},
            ],
        }
        messages = [*self.overrides.get("history_messages", []), user, assistant]
        return {
            "info": {"id": session, "model": {"providerID": model[0], "id": model[1]}},
            "messages": messages,
        }


def answer_for(packet, key, option="correct", evidence='Install "first".'):
    choice = key["correct_id"] if option == "correct" else option
    return json.dumps(
        {
            "opaque_id": packet["opaque_id"],
            "option_id": choice,
            "support": "explicit",
            "evidence": evidence,
            "rationale": "",
        }
    )


def run_one(
    tmp_path, cli, *, pass_number=1, budget=10, packet=None, key=None, **kwargs
):
    if packet is None:
        packet, key = packet_and_key()
    isolation = runner.preflight(CONFIG, cli)
    with runner.Ledger(tmp_path, budget) as ledger:
        return runner.run_assignment(
            packet,
            key,
            pass_number=pass_number,
            output=tmp_path,
            ledger=ledger,
            config=kwargs.pop("config", CONFIG),
            isolation=isolation,
            executor=cli,
            **kwargs,
        )


def test_config_is_deny_all_and_pinned():
    config = runner.opencode_config(CONFIG)
    assert config["permission"] == {"*": "deny"}
    agent = config["agent"]["evaluator"]
    assert agent["tools"] == {"*": False} and "steps" not in agent
    assert config["share"] == "disabled" and config["compaction"] == {
        "auto": False,
        "prune": False,
    }
    assert config["small_model"] == config["model"] == "opencode-go/glm-5.3-flash"
    assert (
        config["mcp"] == {} and config["plugin"] == [] and config["instructions"] == []
    )
    record = runner.configuration_record(CONFIG, "1.18.32")
    assert (
        record["config_sha256"]
        == runner.configuration_record(CONFIG, "1.18.32")["config_sha256"]
    )
    assert "unknown" in record["weights"]


def test_environment_strips_inherited_opencode_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENCODE_PERMISSION", '{"*":"allow"}')
    monkeypatch.setenv("OPENCODE_ENABLE_EXA", "1")
    env = runner.isolated_env(tmp_path, tmp_path / "c.json", tmp_path / "db")
    assert "OPENCODE_PERMISSION" not in env and "OPENCODE_ENABLE_EXA" not in env
    assert (
        env["PWD"] == str(tmp_path / "work")
        and env["OPENCODE_DISABLE_CLAUDE_CODE"] == "1"
    )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"version": "1.19.0"}, "version"),
        ({"config": {"mcp": {"x": {}}}}, "differs"),
        (
            {"skills": [{"name": "docx", "location": "/home/.claude/skills/docx"}]},
            "External skills",
        ),
        ({"tools": {"read": True}}, "enabled tools"),
        ({"history": '[{"id": "old"}]'}, "not empty"),
    ],
)
def test_preflight_fails_closed(overrides, message):
    with pytest.raises(runner.RunnerError, match=message):
        runner.preflight(CONFIG, FakeCLI(**overrides))


def test_success_scores_exactly_and_uses_fresh_sessions(tmp_path):
    packet, key = packet_and_key()
    cli = FakeCLI(answer_for(packet, key))
    outcome = run_one(tmp_path, cli, packet=packet, key=key)
    assert outcome.status == "recorded" and outcome.score == 3
    run_call = next(call for call in cli.calls if call["args"][1] == "run")
    assert run_call["input"] == runner.packet_text(packet)
    assert (
        "correct_id" not in run_call["input"]
        and key["correct_id"] not in run_call["args"]
    )
    assert not {"--continue", "--session", "--fork", "--share", "--auto"} & set(
        run_call["args"]
    )
    attempt = next((tmp_path / "m1_ai_attempts").iterdir())
    assert {p.name for p in attempt.iterdir()} >= {
        "packet.txt",
        "events.jsonl",
        "export.json",
        "result.json",
    }
    # Duplicate first pass is not rerun; the repeat gets a new session and same packet.
    assert run_one(tmp_path, cli, packet=packet, key=key).status == "already_recorded"
    repeat = run_one(tmp_path, cli, packet=packet, key=key, pass_number=2)
    assert repeat.status == "recorded" and repeat.session_id != outcome.session_id
    assert len((tmp_path / "m1_ai.csv").read_text().splitlines()) == 3


@pytest.mark.parametrize(
    ("answer", "overrides", "status"),
    [
        ("not json", {}, "malformed_json"),
        ('```json\n{"a": 1}\n```', {}, "malformed_json"),
        (
            None,
            {
                "extra_events": [
                    json.dumps(
                        {
                            "type": "tool_use",
                            "sessionID": "ses_1",
                            "part": {"tool": "read"},
                        }
                    )
                ]
            },
            "tool_use",
        ),
        (
            None,
            {"model": ("cline-pass", "cline-pass/glm-5.3-flash")},
            "isolation_or_output_check",
        ),
        (None, {"reason": "length"}, "isolation_or_output_check"),
        (
            None,
            {"history_messages": [{"info": {"role": "user"}, "parts": []}]},
            "isolation_or_output_check",
        ),
        ("EVIDENCE", {}, "invalid_response"),
        (None, {"exit": 1}, "exit_status"),
    ],
)
def test_failures_are_retained_not_recorded(tmp_path, answer, overrides, status):
    packet, key = packet_and_key()
    if answer is None:
        answer = answer_for(packet, key)
    elif answer == "EVIDENCE":
        answer = answer_for(packet, key, evidence="Invented quote")
    outcome = run_one(tmp_path, FakeCLI(answer, **overrides), packet=packet, key=key)
    assert outcome.status == status
    assert not (tmp_path / "m1_ai.csv").exists()
    result = json.loads(
        next((tmp_path / "m1_ai_attempts").iterdir())
        .joinpath("result.json")
        .read_text()
    )
    assert result["status"] == status


def test_fenced_json_is_the_only_tolerance():
    assert runner.parse_answer('```json\n{"a": "1"}\n```') == {"a": "1"}
    with pytest.raises(ValueError):
        runner.parse_answer('Here: {"a": "1"}')


def test_invalid_answers_are_final_and_transport_retries_are_bounded(tmp_path):
    packet, key = packet_and_key()
    bad = FakeCLI("not json")
    assert run_one(tmp_path, bad, packet=packet, key=key).status == "malformed_json"
    assert (
        run_one(
            tmp_path, FakeCLI(answer_for(packet, key)), packet=packet, key=key
        ).status
        == "retained_failure"
    )
    other = tmp_path / "other"
    slow = FakeCLI(timeout=True)
    assert run_one(other, slow, packet=packet, key=key).status == "timeout"
    assert run_one(other, slow, packet=packet, key=key).status == "timeout"
    assert run_one(other, slow, packet=packet, key=key).status == "attempts_exhausted"


def test_budget_quota_and_oversize_stop(tmp_path):
    packet, key = packet_and_key()
    with pytest.raises(runner.RunnerError, match="budget"):
        run_one(tmp_path, FakeCLI(answer_for(packet, key)), budget=0)
    quota = json.dumps(
        {
            "type": "error",
            "sessionID": "ses_1",
            "error": {"name": "APIError", "data": {"message": "429 quota exceeded"}},
        }
    )
    with pytest.raises(runner.RunnerError, match="quota"):
        run_one(tmp_path / "q", FakeCLI(events=quota + "\n", exit=1))
    small = runner.RunnerConfig(binary="opencode", max_packet_bytes=10)
    assert run_one(tmp_path / "o", FakeCLI("x"), config=small).status == "oversize"


def test_single_writer_lock(tmp_path):
    with (
        runner.Ledger(tmp_path, 1),
        pytest.raises(runner.RunnerError, match="writer"),
    ):
        runner.Ledger(tmp_path, 1).__enter__()


def test_crash_between_json_and_csv_is_reconciled(tmp_path):
    packet, key = packet_and_key()
    run_one(tmp_path, FakeCLI(answer_for(packet, key)), packet=packet, key=key)
    csv_path = tmp_path / "m1_ai.csv"
    header = csv_path.read_text().splitlines()[0]
    csv_path.write_text(header + "\n")
    assert runner.reconcile(tmp_path)["missing_rows"] == 1
    runner.reconcile(tmp_path, apply=True)
    assert runner.reconcile(tmp_path)["missing_rows"] == 0
    assert len(csv_path.read_text().splitlines()) == 2


def test_batch_keys_must_match_packets(tmp_path):
    packet, key = packet_and_key()
    (tmp_path / "p.jsonl").write_text(json.dumps(packet) + "\n")
    (tmp_path / "k.jsonl").write_text(
        json.dumps({**key, "opaque_id": "AI-other"}) + "\n"
    )
    with pytest.raises(runner.RunnerError, match="one-to-one"):
        runner.load_batch(tmp_path / "p.jsonl", tmp_path / "k.jsonl")


FAKE_PROVIDER = Path(__file__).parent / "fixtures" / "fake_openai_provider.py"


@pytest.mark.skipif(
    os.environ.get("DTS_OPENCODE_LOOPBACK") != "1"
    or not runner.DEFAULT_BINARY.exists(),
    reason="set DTS_OPENCODE_LOOPBACK=1 to run the real CLI against a loopback fake provider",
)
def test_real_cli_against_loopback_provider(tmp_path):
    import socket
    import time

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    packet, key = packet_and_key()
    log = tmp_path / "requests.jsonl"
    server = subprocess.Popen(
        [
            sys.executable,
            str(FAKE_PROVIDER),
            str(port),
            str(log),
            answer_for(packet, key),
        ]
    )
    try:
        time.sleep(0.5)
        config = runner.RunnerConfig(
            provider="loopback",
            provider_override={
                "npm": "@ai-sdk/openai-compatible",
                "options": {
                    "baseURL": f"http://127.0.0.1:{port}/v1",
                    "apiKey": "dummy",
                },
                "models": {
                    "glm-5.3-flash": {
                        "limit": {"context": 1000000, "output": 131072},
                        "temperature": True,
                        "reasoning": True,
                    }
                },
            },
        )
        counts = runner.run_batch(
            [(packet, key)],
            pass_number=1,
            output=tmp_path / "out",
            config=config,
            max_invocations=1,
        )
    finally:
        server.kill()
    assert counts == {"recorded": 1}
    requests = [json.loads(line) for line in log.read_text().splitlines()]
    assert len(requests) == 1
    body = requests[0]["body"]
    assert "tools" not in body and body["temperature"] == 0
    system, user = body["messages"]
    assert user == {"role": "user", "content": runner.packet_text(packet)}
    assert system["content"].startswith(runner.AGENT_PROMPT)
    assert "Is directory a git repo: no" in system["content"]
    assert str(runner.REPO_ROOT) not in system["content"]


def test_smoke_is_bounded_and_outside_repository(tmp_path, monkeypatch):
    with pytest.raises(runner.RunnerError, match="outside the repository"):
        runner.smoke(runner.REPO_ROOT / "build" / "smoke", CONFIG)
    seen = []

    def fake_batch(batch, **kwargs):
        seen.append((len(batch), kwargs["max_invocations"], kwargs["pass_number"]))
        return {"recorded": len(batch)}

    monkeypatch.setattr(runner, "run_batch", fake_batch)
    runner.smoke(tmp_path / "smoke", CONFIG)
    assert seen == [(3, 6, 1), (1, 6, 2)]
