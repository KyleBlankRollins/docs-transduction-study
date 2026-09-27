import json
import subprocess
from collections import Counter

from docs_transduction_study import opencode_runner as runner
from docs_transduction_study import quote_audit as audit

CONFIG = runner.RunnerConfig(
    binary="opencode", provider="opencode-go", model="deepseek-v4-pro"
)


def records():
    rows = []
    for arm in ("explicit", "implicit"):
        for stage, count in (("A1", 60), ("A2", 30), ("A4", 10)):
            for n in range(count):
                rows.append(
                    {
                        "opaque_id": f"AI-{arm}-{stage}-{n}",
                        "assignment_id": f"S01-R1-{n:03d}|{arm}|{stage}",
                        "pass_number": 1,
                        "flags": ["explicit_quote_unverified"],
                    }
                )
    rows.append({**rows[0], "flags": []})
    return rows


def test_sample_is_stratified_per_arm_and_deterministic():
    sample = audit.draw_sample(records(), "seed", per_arm=20)
    assert sample == audit.draw_sample(list(reversed(records())), "seed", per_arm=20)
    counts = Counter(
        (r["assignment_id"].split("|")[1], r["assignment_id"].split("|")[2])
        for r in sample
    )
    assert (
        counts[("explicit", "A1")] == 12
        and counts[("explicit", "A2")] == 6
        and counts[("explicit", "A4")] == 2
    )
    assert sum(v for (arm, _), v in counts.items() if arm == "implicit") == 20


class FakeCLI:
    def __init__(self, category):
        self.category = category
        self.sent = None

    def __call__(self, args, *, input, cwd, env, timeout, stdout_path=None):
        if args[1] == "run":
            self.sent = input
            tag = args[args.index("--title") + 1]
            answer = json.dumps(
                {"item_id": tag, "category": self.category, "rationale": "r"}
            )
            events = [
                {
                    "type": "step_start",
                    "sessionID": "ses_1",
                    "part": {"type": "step-start"},
                },
                {
                    "type": "text",
                    "sessionID": "ses_1",
                    "part": {"type": "text", "text": answer},
                },
                {
                    "type": "step_finish",
                    "sessionID": "ses_1",
                    "part": {"type": "step-finish", "reason": "stop"},
                },
            ]
            out = "".join(json.dumps(e) + "\n" for e in events)
        else:
            model = {"providerID": "opencode-go", "id": "deepseek-v4-pro"}
            out = json.dumps(
                {
                    "info": {"id": "ses_1", "model": model},
                    "messages": [
                        {
                            "info": {"role": "user"},
                            "parts": [{"type": "text", "text": self.sent}],
                        },
                        {
                            "info": {
                                "role": "assistant",
                                "mode": "evaluator",
                                "providerID": "opencode-go",
                                "modelID": "deepseek-v4-pro",
                            },
                            "parts": [{"type": "text"}],
                        },
                    ],
                }
            )
        if stdout_path:
            stdout_path.write_text(out)
        return subprocess.CompletedProcess(args, 0, out, "")


def test_ask_records_valid_categories_and_rejects_others(tmp_path):
    packet = {"item_id": "Q-abc", "quote": "q", "page_text": "p", "options": []}
    with runner.Ledger(tmp_path, 5) as ledger:
        assert (
            audit.ask(
                packet,
                output=tmp_path,
                ledger=ledger,
                config=CONFIG,
                executor=FakeCLI("F"),
            )["status"]
            == "recorded"
        )
        assert (
            audit.ask(
                packet,
                output=tmp_path,
                ledger=ledger,
                config=CONFIG,
                executor=FakeCLI("F"),
            )["status"]
            == "already_recorded"
        )
        other = {**packet, "item_id": "Q-def"}
        assert (
            audit.ask(
                other,
                output=tmp_path,
                ledger=ledger,
                config=CONFIG,
                executor=FakeCLI("X"),
            )["status"]
            == "invalid_response"
        )
    table = audit.summarize(
        tmp_path,
        [
            {"item_id": "Q-abc", "arm": "explicit", "stage": "A1"},
            {"item_id": "Q-def", "arm": "implicit", "stage": "A1"},
        ],
    )
    rows = {(r["arm"], r["stage"]): r for r in table}
    assert (
        rows[("explicit", "all")]["F"] == 1
        and rows[("implicit", "all")]["missing"] == 1
    )
