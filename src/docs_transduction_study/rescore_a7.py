"""Derive amendment-A7 scores from retained M1-AI answers (no evaluator calls).

For every (assignment, pass) the latest attempt that passed isolation and
produced a parsed answer (status ``recorded`` or ``invalid_response``) is
rescored with ``coding_ai.score_response_a7``. Output is derived, deterministic,
and separate from the append-only strict records: ``coding/m1_ai_a7_records/``
and ``coding/m1_ai_a7.csv``. Each row keeps the strict score (or the strict
error) beside the A7 score and flags, so both versions can be reported.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from docs_transduction_study import coding_ai

REPO_ROOT = Path(__file__).resolve().parents[2]
RECORDS_DIR = "m1_ai_a7_records"
USABLE = {"recorded", "invalid_response"}
FIELDS = [
    "opaque_id",
    "assignment_id",
    "pass_number",
    "session_id",
    "score",
    "score_strict",
    "strict_error",
    "flags",
    "attempt",
]


def evaluator_label(configuration: dict[str, Any]) -> str:
    """Evaluator name by transport (amendment A9); OpenCode labels are unchanged."""
    if configuration.get("transport", "").startswith("anthropic-batch"):
        return f"anthropic-batch:{configuration['model']}"
    return f"opencode:{configuration['provider']}/{configuration['model']}"


def latest_answers(coding: Path) -> dict[tuple[str, int], Path]:
    """Latest usable attempt directory per (opaque ID, pass)."""
    chosen: dict[tuple[str, int], tuple[int, Path]] = {}
    for attempt in sorted((coding / "m1_ai_attempts").iterdir()):
        result = json.loads((attempt / "result.json").read_text(encoding="utf-8"))
        if result["status"] not in USABLE or not (attempt / "answer.json").exists():
            continue
        opaque, pass_part, number = attempt.name.rsplit("-", 2)
        key = (opaque, int(pass_part[1:]))
        index = int(number[1:])
        if key not in chosen or index > chosen[key][0]:
            chosen[key] = (index, attempt)
    return {key: path for key, (_, path) in chosen.items()}


def rescore(coding: Path, keys: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    invalid: list[dict[str, str]] = []
    staging = Path(tempfile.mkdtemp(prefix="a7-", dir=coding))
    try:
        for (opaque, pass_number), attempt in sorted(latest_answers(coding).items()):
            packet = json.loads((attempt / "packet.txt").read_text(encoding="utf-8"))
            answer = json.loads((attempt / "answer.json").read_text(encoding="utf-8"))
            result = json.loads((attempt / "result.json").read_text(encoding="utf-8"))
            key = keys[opaque]
            try:
                score, flags = coding_ai.score_response_a7(packet, key, answer)
            except ValueError as error:
                invalid.append({"attempt": attempt.name, "error": str(error)})
                continue
            try:
                strict: int | None = coding_ai.score_response(packet, key, answer)
                strict_error = ""
            except ValueError as error:
                strict, strict_error = None, str(error)
            record = {
                "protocol": coding_ai.A7_VERSION,
                "opaque_id": opaque,
                "assignment_id": key["assignment_id"],
                "pass_number": pass_number,
                "session_id": result["session_id"],
                "evaluator": evaluator_label(result["configuration"]),
                "configuration": result["configuration"],
                "isolation_verified": True,
                "packet_sha256": key["packet_sha256"],
                "score": score,
                "score_strict": strict,
                "strict_error": strict_error,
                "flags": flags,
                "attempt": attempt.name,
                "response": answer,
            }
            (staging / f"{opaque}-p{pass_number}.json").write_text(
                json.dumps(record, indent=2), encoding="utf-8"
            )
            rows.append(
                {name: record[name] for name in FIELDS} | {"flags": ";".join(flags)}
            )
        target = coding / RECORDS_DIR
        shutil.rmtree(target, ignore_errors=True)
        staging.rename(target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    with (coding / "m1_ai_a7.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (coding / "m1_ai_a7_invalid.json").write_text(
        json.dumps(invalid, indent=2), encoding="utf-8"
    )
    return {"rescored": len(rows), "still_invalid": len(invalid)}


def main() -> None:
    from docs_transduction_study.study_pipeline import unseal

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coding", type=Path, default=REPO_ROOT / "coding")
    parser.add_argument(
        "--keys",
        type=Path,
        default=REPO_ROOT / "artifacts" / "private" / "keys.jsonl.enc",
    )
    parser.add_argument("--passphrase-file", type=Path, required=True)
    args = parser.parse_args()
    text = unseal(args.keys, args.passphrase_file.expanduser()).decode("utf-8")
    keys = {
        entry["opaque_id"]: entry
        for entry in map(json.loads, text.splitlines())
        if entry
    }
    print(json.dumps(rescore(args.coding, keys), indent=2))


if __name__ == "__main__":
    main()
