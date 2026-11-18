"""Closed-book covariate for M1-AI (amendment A11).

Each locked first-pass packet is reused without its artifact: same question,
options, and option order, a fixed closed-book instruction, and a new opaque
ID. Keys are sealed separately. Answers are scored only by the chosen option
(correct, foil, declined) and stored apart from M1-AI records. The analysis
follows the A11 pre-specification and reuses the E1-E7 statistics.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

from docs_transduction_study import coding_ai
from docs_transduction_study import exploratory_plan as ep

CB_PROTOCOL = "m1-ai-cb-1"
CB_INSTRUCTION = (
    "No artifact is supplied. Answer from your own knowledge of the Astro "
    "documentation (docs.astro.build), which the question refers to. Do not use "
    "tools, repository files, other assignments, or prior responses. Choose exactly "
    'one option by its id. If you do not know, choose "The text does not say". '
    "Report support as inferred with a brief rationale, or as absent when you choose "
    '"The text does not say"; leave evidence empty. Return only JSON with opaque_id, '
    "option_id, support, evidence, and rationale."
)
RECORDS_DIR = "closed_book_records"
FIELDS = {"opaque_id", "option_id", "support", "evidence", "rationale"}
KNOWN_MIN = 5  # of 8 closed-book answers per instance
EVALUATORS = {
    "glm-5.3-flash": (Path("coding"), Path("coding/glm-5.3-flash-closed-book")),
    "claude-sonnet-5-5": (
        Path("coding/claude-sonnet-5-5"),
        Path("coding/claude-sonnet-5-5-closed-book"),
    ),
}
LABEL = (
    "Pre-specified closed-book covariate analysis (amendment A11). Exploratory, "
    "model-conditioned M1-AI; evaluators not pooled."
)


def _sha(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def instruction_sha(protocol: str) -> str:
    text = CB_INSTRUCTION if protocol == CB_PROTOCOL else coding_ai.EVALUATOR_PROMPT
    return hashlib.sha256(text.encode()).hexdigest()


# ── Packets and keys ───────────────────────────────────────────────────────


def closed_book_packet(
    packet: dict[str, Any], key: dict[str, Any], seed: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """The packet without its artifact, and its separate scoring key."""
    if _sha(packet) != key["packet_sha256"] or packet["opaque_id"] != key["opaque_id"]:
        raise ValueError("Source packet does not match its key")
    identifier = coding_ai.opaque_id(f"{key['assignment_id']}|closed-book", seed)
    cb = {
        "protocol": CB_PROTOCOL,
        "instruction": CB_INSTRUCTION,
        "opaque_id": identifier,
        "question": packet["question"],
        "options": packet["options"],
    }
    cb_key = {
        "opaque_id": identifier,
        "assignment_id": key["assignment_id"],
        "source_opaque_id": packet["opaque_id"],
        "correct_id": key["correct_id"],
        "absent_id": key["absent_id"],
        "packet_sha256": _sha(cb),
    }
    return cb, cb_key


def build(
    packets: Path,
    keys: Path,
    passphrase_file: Path,
    out_packets: Path,
    out_keys: Path,
    seed: str,
) -> dict[str, Any]:
    from docs_transduction_study.opencode_runner import load_batch
    from docs_transduction_study.study_pipeline import _seal

    pairs = load_batch(packets, keys, passphrase_file)
    built = [closed_book_packet(packet, key, seed) for packet, key in pairs]
    if len({cb["opaque_id"] for cb, _ in built}) != len(built):
        raise ValueError("Closed-book opaque IDs collide")
    out_packets.write_text(
        "".join(json.dumps(cb, ensure_ascii=False) + "\n" for cb, _ in built),
        encoding="utf-8",
    )
    plaintext = "".join(json.dumps(k) + "\n" for _, k in built).encode()
    out_keys.write_bytes(_seal(plaintext, passphrase_file.expanduser()))
    return {"packets": len(built), "out": str(out_packets), "keys": str(out_keys)}


# ── Scoring and records ────────────────────────────────────────────────────


def score_closed_book(
    packet: dict[str, Any], key: dict[str, Any], response: dict[str, str]
) -> tuple[str, list[str]]:
    """Outcome by chosen option; structural problems raise ValueError."""
    if (
        _sha(packet) != key["packet_sha256"]
        or response.get("opaque_id") != key["opaque_id"]
    ):
        raise ValueError("Packet or response identity mismatch")
    if set(response) != FIELDS:
        raise ValueError("Response fields do not match protocol")
    choice = response["option_id"]
    if choice not in {option["id"] for option in packet["options"]}:
        raise ValueError("Unknown option")
    support = response["support"]
    if support not in {"explicit", "inferred", "absent"}:
        raise ValueError("Unknown support type")
    flags = []
    if response["evidence"].strip():
        flags.append("evidence_not_empty")
    if choice == key["absent_id"]:
        if support != "absent":
            flags.append("declined_without_absent_support")
        return "cb_declined", flags
    if support != "inferred":
        flags.append("support_not_inferred")
    return ("cb_correct" if choice == key["correct_id"] else "cb_foil"), flags


def record_closed_book(
    output: Path,
    packet: dict[str, Any],
    key: dict[str, Any],
    response: dict[str, str],
    *,
    pass_number: int,
    session_id: str,
    evaluator: str,
    configuration: dict[str, Any],
    isolation_verified: bool,
) -> dict[str, Any]:
    """Append-only record; same signature as ``coding_ai.record_response``."""
    if pass_number != 1 or not session_id or not evaluator or not configuration:
        raise ValueError("Complete evaluator provenance and pass 1 are required")
    if not isolation_verified:
        raise ValueError("Isolated evaluator evidence is required")
    outcome, flags = score_closed_book(packet, key, response)
    records = output / RECORDS_DIR
    records.mkdir(parents=True, exist_ok=True)
    for path in records.glob("*.json"):
        if json.loads(path.read_text(encoding="utf-8"))["session_id"] == session_id:
            raise ValueError("Each assignment requires a fresh evaluator session")
    record = {
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "protocol": CB_PROTOCOL,
        "opaque_id": packet["opaque_id"],
        "assignment_id": key["assignment_id"],
        "pass_number": pass_number,
        "session_id": session_id,
        "evaluator": evaluator,
        "configuration": configuration,
        "isolation_verified": isolation_verified,
        "packet_sha256": key["packet_sha256"],
        "packet": packet,
        "response": response,
        "outcome": outcome,
        "flags": flags,
    }
    name = hashlib.sha256(f"cb-record:{packet['opaque_id']}".encode()).hexdigest()
    with (records / f"{name}.json").open("x", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)
    return {"score": outcome, "flags": flags}


Recorder = Callable[..., dict[str, Any]]


def recorder_for(protocol: str) -> tuple[Recorder, str]:
    """The record function and records directory for a packet protocol."""
    if protocol == CB_PROTOCOL:
        return record_closed_book, RECORDS_DIR
    return coding_ai.record_response, coding_ai.RECORDS_DIR


# ── Analysis (A11 pre-specification) ───────────────────────────────────────


def load_outcomes(cb_coding: Path) -> dict[str, str]:
    """Closed-book outcome by assignment ID."""
    out = {}
    for path in sorted((cb_coding / RECORDS_DIR).glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        out[record["assignment_id"]] = record["outcome"]
    return out


def known_instances(
    outcomes: dict[str, str], instances: dict[str, dict[str, str]]
) -> list[dict[str, Any]]:
    """Known = closed-book correct in at least 5 of its 8 assignments."""
    answers: dict[str, list[str]] = defaultdict(list)
    for assignment_id, outcome in outcomes.items():
        answers[assignment_id.split("|")[0]].append(outcome)
    rows = []
    for instance_id in sorted(instances):
        given = answers.get(instance_id, [])
        correct = given.count("cb_correct")
        rows.append(
            {
                "instance_id": instance_id,
                "relation": instances[instance_id]["relation_type"],
                "specimen_id": instances[instance_id]["specimen_id"],
                "answers": len(given),
                "cb_correct": correct,
                "cb_foil": given.count("cb_foil"),
                "cb_declined": given.count("cb_declined"),
                "known": correct >= KNOWN_MIN,
            }
        )
    return rows


def accuracy(known: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for relation in ("all", *ep.RELATIONS):
        here = [k for k in known if relation in ("all", k["relation"])]
        answers = sum(k["answers"] for k in here)
        rows.append(
            {
                "relation": relation,
                "instances": len(here),
                "answers": answers,
                "expected_answers": 8 * len(here),
                **{
                    f"{o}_rate": ep._ratio(sum(k[o] for k in here), answers)
                    for o in ("cb_correct", "cb_foil", "cb_declined")
                },
                "known_instances": sum(k["known"] for k in here),
            }
        )
    return rows


def crosstab(rows: list[ep.Row], outcomes: dict[str, str]) -> list[dict[str, Any]]:
    out = []
    for stage in ep.STAGES:
        for arm in ep.ARMS:
            cells: Counter[str] = Counter()
            for r in rows:
                if r["stage"] != stage or r["arm"] != arm:
                    continue
                cb = outcomes.get(f"{r['instance_id']}|{arm}|{stage}")
                if cb is None:
                    cells["closed_book_missing"] += 1
                    continue
                open_ok, cb_ok = ep.correct(r["score"]), cb == "cb_correct"
                cells[
                    "known_both_correct"
                    if open_ok and cb_ok
                    else "recovered_from_artifact"
                    if open_ok
                    else "lost_despite_knowledge"
                    if cb_ok
                    else "correct_in_neither"
                ] += 1
            out.append({"stage": stage, "arm": arm, **cells})
    return out


def unknown_gaps(
    rows: list[ep.Row], known: list[dict[str, Any]], boot: ep.Bootstrap
) -> dict[str, list[ep.Row]]:
    unknown = {k["instance_id"] for k in known if not k["known"]}
    pairs, _ = ep.make_pairs([r for r in rows if r["instance_id"] in unknown])
    keep = {"correct", "quotable_conditional"}
    return {
        "e1": [r for r in ep.e1(pairs, boot) if r["outcome"] in keep],
        "e2_gaps": [r for r in ep.e2_gaps(pairs, boot) if r["outcome"] in keep],
        "e6_gaps": [],
        "unknown_instances": [{"n": len(unknown), "complete_pairs": len(pairs)}],
    }


def familiarity(
    rows: list[ep.Row], outcomes: dict[str, str], boot: ep.Bootstrap
) -> list[dict[str, Any]]:
    """Explicit-minus-implicit gap in 'lost despite knowledge', per stage."""
    lost = []
    for r in rows:
        cb = outcomes.get(f"{r['instance_id']}|{r['arm']}|{r['stage']}")
        if cb is None:
            continue
        flag = int(not ep.correct(r["score"]) and cb == "cb_correct")
        lost.append({**r, "score": flag})
    pairs, _ = ep.make_pairs(lost)
    out = []
    for stage in ep.STAGES:
        here = [p for p in pairs if p["stage"] == stage]
        stat = ep.paired_gap(here, lambda s: s)
        out.append({"stage": stage, "n_pairs": len(here), **boot.summarize(stat)})
    return out


def single_evaluator_robustness(tables: dict[str, list[ep.Row]]) -> list[ep.Row]:
    """Specimen criterion alone (one evaluator); labelled as such."""
    out = []
    for table in ("e1", "e2_gaps"):
        for row in tables[table]:
            sign = ep._sign(row["point"])
            field = {-1: "specimens_negative", 1: "specimens_positive"}.get(sign or 0)
            out.append(
                {
                    "table": table,
                    "stage": row["stage"],
                    "outcome": row["outcome"],
                    "quantity": row.get("quantity", ""),
                    "point": row["point"],
                    "specimens_with_sign": row[field] if field else None,
                    "robust_specimen_criterion_only": field is not None
                    and row[field] >= ep.ROBUST_MIN_SPECIMENS,
                }
            )
    return out


def main() -> None:
    from docs_transduction_study import study_pipeline

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="write closed-book packets and sealed keys")
    b.add_argument("--passphrase-file", type=Path, required=True)
    b.add_argument(
        "--packets", type=Path, default=Path("artifacts/assignments/packets.jsonl")
    )
    b.add_argument(
        "--keys", type=Path, default=Path("artifacts/private/keys.jsonl.enc")
    )
    b.add_argument(
        "--out-packets",
        type=Path,
        default=Path("artifacts/assignments/closed_book_packets.jsonl"),
    )
    b.add_argument(
        "--out-keys",
        type=Path,
        default=Path("artifacts/private/closed_book_keys.jsonl.enc"),
    )
    a = sub.add_parser("analyze", help="A11 pre-specified analysis")
    a.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    a.add_argument("--out", type=Path, default=Path("analysis/closed_book_covariate"))
    a.add_argument("--resamples", type=int, default=ep.RESAMPLES)
    args = parser.parse_args()
    instrument = study_pipeline.load_instrument()
    if args.command == "build":
        print(
            json.dumps(
                build(
                    args.packets,
                    args.keys,
                    args.passphrase_file,
                    args.out_packets,
                    args.out_keys,
                    instrument["seed"],
                ),
                indent=2,
            )
        )
        return
    instances = {row["instance_id"]: row for row in instrument["instances"]}
    spans: dict[tuple[str, str], bool] = {}
    for record in json.loads(
        (args.artifacts / "anchor-assignments.json").read_text(encoding="utf-8")
    ):
        for arm in ep.ARMS:
            spans[(record["instance_id"], arm)] = record[arm]["spans_chunks"]
    boot = ep.Bootstrap(
        sorted({r["specimen_id"] for r in instances.values()}),
        args.resamples,
        ep.SEED_STRING,
    )
    gaps: dict[str, dict[str, list[ep.Row]]] = {}
    summary: dict[str, Any] = {"label": LABEL}
    for name, (open_coding, cb_coding) in EVALUATORS.items():
        if not (cb_coding / RECORDS_DIR).exists():
            summary[name] = "no closed-book records; not analyzed"
            continue
        rows = ep.load_rows(open_coding, instances, spans)
        outcomes = load_outcomes(cb_coding)
        known = known_instances(outcomes, instances)
        gaps[name] = unknown_gaps(rows, known, boot)
        out = args.out / name
        for table, data in {
            "accuracy": accuracy(known),
            "known_instances": known,
            "crosstab": crosstab(rows, outcomes),
            "unknown_e1": gaps[name]["e1"],
            "unknown_e2": gaps[name]["e2_gaps"],
            "familiarity": familiarity(rows, outcomes, boot),
        }.items():
            ep.write_csv(out / f"{table}.csv", data)
        summary[name] = {
            "closed_book_answers": len(outcomes),
            "known_instances": sum(k["known"] for k in known),
            **gaps[name]["unknown_instances"][0],
        }
    if len(gaps) == 2:
        ep.write_csv(args.out / "robustness.csv", ep.robustness(gaps))
    else:
        for name, tables in gaps.items():
            ep.write_csv(
                args.out / name / "robustness_specimen_only.csv",
                single_evaluator_robustness(tables),
            )
    (args.out / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
