"""Anthropic Message Batches transport for exploratory M1-AI evaluations (A9).

Amendment A9 adds this configuration as an exploratory replication. Paid runs
still need a separate maintainer approval with a budget and call cap (A3).
Nothing here runs at import time.

Each assignment is one stateless batch request: the pinned ``AGENT_PROMPT`` as
the system prompt and ``packet_text(packet)`` verbatim as the only user message,
with no tools, no history, and no fallback model. Output mirrors the OpenCode
runner's layout inside a separate coding directory (never ``coding/`` itself),
so ``rescore_a7`` and ``analysis --coding-dir`` read it unchanged:

    <coding>/m1_ai_attempts/<opaque>-p<pass>-a<n>/{packet.txt,request.json,
        response.json,answer.json,result.json}
    <coding>/m1_ai_attempts.jsonl   append-only ledger (invoke/result events)
    <coding>/m1_ai_batches.jsonl    submitted batch IDs and their custom IDs
    <coding>/m1_ai_records/, <coding>/m1_ai.csv   via coding_ai.record_response

``submit`` needs only the packets; answer keys are unsealed only by ``collect``.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from docs_transduction_study import coding_ai
from docs_transduction_study.opencode_runner import (
    AGENT_PROMPT,
    Ledger,
    RunnerError,
    _record_exists,
    load_batch,
    next_attempt_dir,
    packet_text,
    parse_answer,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
TRANSPORT_VERSION = "anthropic-batch-runner-1"
# Batch outcomes that may be resubmitted (up to max_attempts); all others are final.
TRANSPORT_FAILURES = {"expired", "api_error", "canceled"}
RETRYABLE_ERRORS = {
    "api_error",
    "overloaded_error",
    "rate_limit_error",
    "timeout_error",
}
# Batch API limits are 100,000 requests / 256 MB; stay well inside both.
MAX_BATCH_REQUESTS = 10_000
MAX_BATCH_BYTES = 100_000_000
# Batch prices per million tokens (50% of standard), cached 2026-11-03.
BATCH_PRICE_PER_MTOK = {
    "claude-sonnet-5-5": (1.00, 5.00),
    "claude-opus-5-5": (2.00, 10.00),
}


@dataclasses.dataclass(frozen=True)
class BatchConfig:
    model: str = "claude-sonnet-5-5"
    # Thinking is adaptive (always on unless disabled); effort is recorded explicitly.
    effort: str = "high"
    # Matches the OpenCode run's 32,000 output cap; thinking counts toward it.
    max_tokens: int = 32_000
    max_packet_bytes: int = 1_500_000

    @property
    def evaluator(self) -> str:
        return f"anthropic-batch:{self.model}"


def configuration_record(config: BatchConfig) -> dict[str, Any]:
    """Pinned evaluator configuration stored with every record (deterministic)."""
    return {
        "transport": TRANSPORT_VERSION,
        "provider": "anthropic",
        "model": config.model,
        "endpoint": "POST /v1/messages/batches",
        "thinking": "adaptive (API default; not sent)",
        "effort": config.effort,
        "max_output_tokens": config.max_tokens,
        "temperature": "provider default (non-default sampling rejected by model)",
        "top_p": "provider default (not set)",
        "seed": "unknown (not supported by API)",
        "weights": "unknown (model alias does not pin weights)",
        "fallbacks": "none (not sent; not allowed in batches)",
        "tools": "none",
        "protocol": coding_ai.PROTOCOL_VERSION,
        "evaluator_prompt_sha256": hashlib.sha256(
            coding_ai.EVALUATOR_PROMPT.encode()
        ).hexdigest(),
        "agent_prompt_sha256": hashlib.sha256(AGENT_PROMPT.encode()).hexdigest(),
    }


def request_params(packet: dict[str, Any], config: BatchConfig) -> dict[str, Any]:
    return {
        "model": config.model,
        "max_tokens": config.max_tokens,
        "system": AGENT_PROMPT,
        "messages": [{"role": "user", "content": packet_text(packet)}],
        "output_config": {"effort": config.effort},
    }


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _append(path: Path, entry: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"at": _now(), **entry}) + "\n")


def _ensure_separate(coding: Path) -> None:
    if coding.resolve() == (REPO_ROOT / "coding").resolve():
        raise RunnerError(
            "Use a separate coding directory; coding/ holds the GLM records"
        )


def pending(
    packets: list[dict[str, Any]],
    ledger_entries: list[dict[str, Any]],
    *,
    pass_number: int,
    max_attempts: int,
) -> list[dict[str, Any]]:
    """Packets eligible for (re)submission under the runner's retry rules."""
    invokes: dict[str, int] = {}
    results: dict[str, list[str]] = {}
    for entry in ledger_entries:
        tag = str(entry.get("tag"))
        if entry["event"] == "invoke":
            invokes[tag] = invokes.get(tag, 0) + 1
        elif entry["event"] == "result":
            results.setdefault(tag, []).append(entry["status"])
    eligible = []
    for packet in packets:
        tag = f"{packet['opaque_id']}-p{pass_number}"
        statuses = results.get(tag, [])
        if invokes.get(tag, 0) > len(statuses):
            continue  # in flight
        if any(status not in TRANSPORT_FAILURES for status in statuses):
            continue  # recorded, or a retained final outcome
        if len(statuses) >= max_attempts:
            continue
        eligible.append(packet)
    return eligible


def chunk(requests: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = [[]]
    size = 0
    for request in requests:
        width = len(json.dumps(request, ensure_ascii=False).encode())
        if chunks[-1] and (
            size + width > MAX_BATCH_BYTES or len(chunks[-1]) >= MAX_BATCH_REQUESTS
        ):
            chunks.append([])
            size = 0
        chunks[-1].append(request)
        size += width
    return [c for c in chunks if c]


def estimate(
    client: Any,
    packets: list[dict[str, Any]],
    config: BatchConfig,
    *,
    output_tokens_per_request: int = 1_500,
) -> dict[str, Any]:
    """Free token count of the exact requests and a projected batch cost."""
    total = 0
    for packet in packets:
        params = request_params(packet, config)
        total += client.messages.count_tokens(
            model=params["model"], system=params["system"], messages=params["messages"]
        ).input_tokens
    price_in, price_out = BATCH_PRICE_PER_MTOK[config.model]
    output = output_tokens_per_request * len(packets)
    return {
        "requests": len(packets),
        "input_tokens": total,
        "assumed_output_tokens": output,
        "projected_batch_usd": round(
            total / 1e6 * price_in + output / 1e6 * price_out, 2
        ),
    }


def submit(
    client: Any,
    packets: list[dict[str, Any]],
    *,
    pass_number: int,
    coding: Path,
    config: BatchConfig,
    max_invocations: int,
    max_attempts: int = 2,
) -> dict[str, Any]:
    """Create batches for eligible packets; the call budget is checked up front."""
    _ensure_separate(coding)
    batches_path = coding / "m1_ai_batches.jsonl"
    with Ledger(coding, max_invocations) as ledger:
        open_submissions = {
            e["submission"] for e in _jsonl(batches_path) if e["event"] == "submitting"
        } - {e["submission"] for e in _jsonl(batches_path) if e["event"] == "submitted"}
        if open_submissions:
            raise RunnerError(
                f"Unconfirmed submissions {sorted(open_submissions)}: check "
                "client.messages.batches.list() before resubmitting (possible billed batch)"
            )
        todo = pending(
            packets,
            ledger.entries(),
            pass_number=pass_number,
            max_attempts=max_attempts,
        )
        if ledger.invocations() + len(todo) > max_invocations:
            raise RunnerError(
                f"{len(todo)} requests exceed the remaining budget "
                f"({max_invocations - ledger.invocations()}); approve a new budget"
            )
        oversize = []
        requests = []
        for packet in todo:
            tag = f"{packet['opaque_id']}-p{pass_number}"
            sent = packet_text(packet)
            if len(sent.encode()) > config.max_packet_bytes:
                ledger.append({"event": "result", "tag": tag, "status": "oversize"})
                oversize.append(tag)
                continue
            attempt_dir, number = next_attempt_dir(coding / "m1_ai_attempts", tag)
            attempt_dir.mkdir(parents=True)
            params = request_params(packet, config)
            (attempt_dir / "packet.txt").write_text(sent, encoding="utf-8")
            (attempt_dir / "request.json").write_text(
                json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            requests.append(
                {
                    "custom_id": attempt_dir.name,
                    "params": params,
                    "_tag": tag,
                    "_n": number,
                }
            )
        created = []
        for index, part in enumerate(chunk(requests)):
            submission = f"{_now()}#{index}"
            custom_ids = [r["custom_id"] for r in part]
            _append(
                batches_path,
                {
                    "event": "submitting",
                    "submission": submission,
                    "custom_ids": custom_ids,
                },
            )
            batch = client.messages.batches.create(
                requests=[
                    {"custom_id": r["custom_id"], "params": r["params"]} for r in part
                ]
            )
            _append(
                batches_path,
                {
                    "event": "submitted",
                    "submission": submission,
                    "batch_id": batch.id,
                    "pass_number": pass_number,
                    "configuration": configuration_record(config),
                },
            )
            for r in part:
                ledger.append(
                    {
                        "event": "invoke",
                        "tag": r["_tag"],
                        "attempt": r["_n"],
                        "batch_id": batch.id,
                    }
                )
            created.append({"batch_id": batch.id, "requests": len(part)})
    return {
        "batches": created,
        "oversize": oversize,
        "skipped": len(packets) - len(todo),
    }


def check_message(message: Any, config: BatchConfig) -> tuple[list[str], str]:
    """Isolation/output problems in one batch response, and its joined text."""
    problems = []
    if message.model != config.model:
        problems.append("wrong_response_model")
    if message.stop_reason != "end_turn":
        problems.append(f"stop_reason:{message.stop_reason}")
    texts = []
    for block in message.content:
        if block.type == "text":
            texts.append(block.text)
        elif block.type != "thinking":
            problems.append(f"unexpected_block:{block.type}")
    if not texts:
        problems.append("no_text")
    return sorted(set(problems)), "".join(texts)


def collect(
    client: Any,
    keys: dict[str, dict[str, Any]],
    *,
    coding: Path,
    config: BatchConfig,
) -> dict[str, Any]:
    """Record every ended, not-yet-collected batch; pending batches are left alone."""
    _ensure_separate(coding)
    batches_path = coding / "m1_ai_batches.jsonl"
    entries = _jsonl(batches_path)
    collected = {e["batch_id"] for e in entries if e["event"] == "collected"}
    counts: dict[str, int] = {}
    waiting = []
    with Ledger(coding, max_invocations=0) as ledger:
        for entry in entries:
            if entry["event"] != "submitted" or entry["batch_id"] in collected:
                continue
            batch_id = entry["batch_id"]
            if entry["configuration"] != configuration_record(config):
                raise RunnerError(f"Batch {batch_id} used a different configuration")
            if client.messages.batches.retrieve(batch_id).processing_status != "ended":
                waiting.append(batch_id)
                continue
            for item in client.messages.batches.results(batch_id):
                attempt_dir = coding / "m1_ai_attempts" / item.custom_id
                opaque, pass_part, _ = item.custom_id.rsplit("-", 2)
                tag = f"{opaque}-{pass_part}"
                if (attempt_dir / "result.json").exists():
                    continue
                status, detail, extra = _record_item(
                    item,
                    attempt_dir,
                    keys[opaque],
                    pass_number=int(pass_part[1:]),
                    coding=coding,
                    config=config,
                )
                (attempt_dir / "result.json").write_text(
                    json.dumps(
                        {
                            "status": status,
                            "detail": detail,
                            "configuration": configuration_record(config),
                            "batch_id": batch_id,
                            **extra,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                ledger.append(
                    {"event": "result", "tag": tag, "status": status, "detail": detail}
                )
                counts[status] = counts.get(status, 0) + 1
            _append(batches_path, {"event": "collected", "batch_id": batch_id})
    return {"counts": counts, "waiting": waiting}


def _record_item(
    item: Any,
    attempt_dir: Path,
    key: dict[str, Any],
    *,
    pass_number: int,
    coding: Path,
    config: BatchConfig,
) -> tuple[str, str, dict[str, Any]]:
    outcome = item.result
    if outcome.type in {"expired", "canceled"}:
        return outcome.type, "", {}
    if outcome.type == "errored":
        error = outcome.error
        kind = getattr(getattr(error, "error", error), "type", "unknown")
        # Only server-side transient errors are retried; validation, auth, and
        # billing errors are final and need a person to look at them.
        status = "api_error" if kind in RETRYABLE_ERRORS else "request_rejected"
        return status, str(kind), {}
    message = outcome.message
    (attempt_dir / "response.json").write_text(
        json.dumps(message.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    extra: dict[str, Any] = {
        "session_id": message.id,
        "usage": message.usage.model_dump(mode="json"),
    }
    problems, text = check_message(message, config)
    if message.stop_reason == "refusal":
        # Final, never retried; documented unscorable under A8 (amendment A9).
        details = getattr(message, "stop_details", None)
        return "refusal", str(getattr(details, "category", "") or ""), extra
    if problems:
        return "isolation_or_output_check", ",".join(problems), extra
    try:
        answer = parse_answer(text)
    except ValueError as error:
        return "malformed_json", str(error), extra
    (attempt_dir / "answer.json").write_text(
        json.dumps(answer, indent=2), encoding="utf-8"
    )
    packet = json.loads((attempt_dir / "packet.txt").read_text(encoding="utf-8"))
    if _record_exists(coding, packet["opaque_id"], pass_number):
        # An interrupted collect recorded this answer but not its result.json.
        return "recorded", "record already retained", extra
    try:
        summary = coding_ai.record_response(
            coding,
            packet,
            key,
            answer,
            pass_number=pass_number,
            session_id=message.id,
            evaluator=config.evaluator,
            configuration=configuration_record(config),
            isolation_verified=True,
        )
    except ValueError as error:
        return "invalid_response", str(error), extra
    return "recorded", "", {**extra, "score": summary["score"]}


def _packets(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def main(argv: list[str] | None = None) -> int:
    import anthropic

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=BatchConfig.model)
    parser.add_argument("--effort", default=BatchConfig.effort)
    sub = parser.add_subparsers(dest="command", required=True)
    est = sub.add_parser("estimate", help="free token count and projected cost")
    est.add_argument("--packets", type=Path, required=True)
    run = sub.add_parser("submit", help="create batches (BILLED once processed)")
    run.add_argument("--packets", type=Path, required=True)
    run.add_argument("--coding", type=Path, required=True)
    run.add_argument("--pass-number", type=int, choices=(1, 2), required=True)
    run.add_argument("--max-invocations", type=int, required=True)
    run.add_argument("--max-attempts", type=int, default=2)
    col = sub.add_parser("collect", help="record results of ended batches")
    col.add_argument("--packets", type=Path, required=True)
    col.add_argument("--keys", type=Path, required=True)
    col.add_argument("--passphrase-file", type=Path, default=None)
    col.add_argument("--coding", type=Path, required=True)
    args = parser.parse_args(argv)
    config = BatchConfig(model=args.model, effort=args.effort)
    client = anthropic.Anthropic()
    if args.command == "estimate":
        result = estimate(client, _packets(args.packets), config)
    elif args.command == "submit":
        result = submit(
            client,
            _packets(args.packets),
            pass_number=args.pass_number,
            coding=args.coding,
            config=config,
            max_invocations=args.max_invocations,
            max_attempts=args.max_attempts,
        )
    else:
        pairs = load_batch(args.packets, args.keys, args.passphrase_file)
        keys = {packet["opaque_id"]: key for packet, key in pairs}
        result = collect(client, keys, coding=args.coding, config=config)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
