"""Generate reviewable O1/O2 candidate CSV with context for human classification."""

from __future__ import annotations

import argparse
import csv
import difflib
import re
from pathlib import Path


def _strip_frontmatter(text: str) -> str:
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
    text = re.sub(r"^import\s+.*?;?\n", "", text, flags=re.MULTILINE)
    return text


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _find_context(
    body: str,
    expression: str,
    window_chars: int = 120,
) -> dict[str, str]:
    norm_body = _normalize(body)
    norm_expr = _normalize(expression)
    idx = norm_body.lower().find(norm_expr.lower())
    if idx == -1:
        pat = re.compile(re.escape(norm_expr), re.IGNORECASE)
        m = pat.search(norm_body)
        if m:
            idx = m.start()
        else:
            return {}
    before_start = max(0, idx - window_chars)
    after_end = min(len(norm_body), idx + len(norm_expr) + window_chars)
    return {
        "before": norm_body[before_start:idx].strip(),
        "after": norm_body[idx + len(norm_expr) : after_end].strip(),
    }


def _find_source_line(body: str, expression: str) -> int:
    norm_expr = _normalize(expression).lower()
    for i, line in enumerate(body.split("\n")):
        if norm_expr in _normalize(line).lower():
            return i + 1
    return 0


def occurrence_context(text: str, expression: str, notes: str) -> dict[str, str]:
    match = re.search(r"A0 chars \[(\d+),(\d+)\)", notes)
    if match is None:
        raise ValueError("Occurrence is missing source offsets")
    start, end = map(int, match.groups())
    if text[start:end].strip() != expression:
        raise ValueError("Occurrence offsets do not match source expression")
    return {
        "before": _normalize(text[max(0, start - 240) : start])[-120:],
        "after": _normalize(text[end : end + 240])[:120],
        "source_line": str(text[:start].count("\n") + 1),
    }


def pair_occurrences(
    explicit: str, implicit: str, spans: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Map unchanged occurrence tokens across a surgical source transformation."""
    source_tokens = list(re.finditer(r"\w+|[^\w\s]", explicit))
    target_tokens = list(re.finditer(r"\w+|[^\w\s]", implicit))
    blocks = difflib.SequenceMatcher(
        None,
        [token.group() for token in source_tokens],
        [token.group() for token in target_tokens],
        autojunk=False,
    ).get_matching_blocks()
    paired: list[tuple[int, int]] = []
    for start, end in spans:
        indices = [
            index
            for index, token in enumerate(source_tokens)
            if token.start() < end and start < token.end()
        ]
        if not indices:
            raise ValueError(f"Empty occurrence [{start},{end})")
        matches = [
            block
            for block in blocks
            if block.a <= indices[0] and indices[-1] < block.a + block.size
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Occurrence [{start},{end}) needs explicit cross-arm review"
            )
        block = matches[0]
        target_start = (
            target_tokens[block.b + indices[0] - block.a].start()
            + start
            - source_tokens[indices[0]].start()
        )
        target_end = (
            target_tokens[block.b + indices[-1] - block.a].end()
            + end
            - source_tokens[indices[-1]].end()
        )
        if _normalize(explicit[start:end]) != _normalize(
            implicit[target_start:target_end]
        ):
            raise ValueError(f"Occurrence [{start},{end}) changed across arms")
        paired.append((target_start, target_end))
    if len(set(paired)) != len(paired):
        raise ValueError("Distinct occurrences collapsed during pairing")
    return paired


OUTPUT_FIELDS = [
    "instance_id",
    "specimen_id",
    "relation_type",
    "expression",
    "context_before",
    "highlight",
    "context_after",
    "source_line",
    "accept",
    "rejection_reason",
    "explicit_start",
    "explicit_end",
    "implicit_start",
    "implicit_end",
]


def generate_review_csv(
    instances_csv: Path,
    explicit_dir: Path,
    output: Path,
    relation_type: str = "O1",
) -> None:
    """Generate review CSV for candidates of one relation type."""
    spec_paths: dict[str, str] = {}
    spec_csv = instances_csv.parent.parent / "corpus" / "specimens.csv"
    if spec_csv.exists():
        with spec_csv.open("r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                spec_paths[row["specimen_id"]] = row["source_path"]

    with instances_csv.open("r", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))
    candidates = [r for r in all_rows if r["relation_type"] == relation_type]

    paired_offsets: dict[str, tuple[int, int, int, int]] = {}
    for sid, specimen_path in spec_paths.items():
        positional = [
            row
            for row in candidates
            if row["specimen_id"] == sid and "A0 chars [" in row["notes"]
        ]
        if not positional:
            continue
        explicit_text = (explicit_dir / specimen_path).read_text(encoding="utf-8")
        implicit_text = (explicit_dir.parent / "implicit" / specimen_path).read_text(
            encoding="utf-8"
        )
        spans = []
        for row in positional:
            match = re.search(r"A0 chars \[(\d+),(\d+)\)", row["notes"])
            if match is None:
                raise ValueError("Missing occurrence offsets")
            spans.append((int(match[1]), int(match[2])))
        paired = pair_occurrences(explicit_text, implicit_text, spans)
        for row, source_span, target_span in zip(
            positional, spans, paired, strict=True
        ):
            paired_offsets[row["instance_id"]] = (*source_span, *target_span)

    if not candidates:
        print(f"No {relation_type} candidates found")
        return

    print(f"Generating review for {len(candidates)} {relation_type} candidates...")
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()

        for row in candidates:
            inst_id = row["instance_id"]
            sid = row["specimen_id"]
            notes = row["notes"]

            m = re.search(r"'([^']+)'", notes)
            expr = m.group(1) if m else notes

            source_path = spec_paths.get(sid)
            before = ""
            after = ""
            source_line = 0
            offsets = paired_offsets.get(inst_id)
            if "A0 chars [" in notes and offsets is None:
                raise ValueError(f"Missing paired source for {inst_id}")

            if source_path:
                source_file = explicit_dir / source_path
                if source_file.exists():
                    text = source_file.read_text(encoding="utf-8")
                    if "A0 chars [" in notes:
                        ctx = occurrence_context(text, expr, notes)
                        source_line = int(ctx["source_line"])
                    else:
                        body = _strip_frontmatter(text)
                        ctx = _find_context(body, expr)
                        source_line = _find_source_line(body, expr)
                    before = ctx.get("before", "")
                    after = ctx.get("after", "")

            writer.writerow(
                {
                    "instance_id": inst_id,
                    "specimen_id": sid,
                    "relation_type": relation_type,
                    "expression": expr,
                    "context_before": before[-120:].strip(),
                    "highlight": expr,
                    "context_after": after[:120].strip(),
                    "source_line": str(source_line) if source_line else "",
                    "accept": "",
                    "rejection_reason": "",
                    "explicit_start": str(offsets[0]) if offsets else "",
                    "explicit_end": str(offsets[1]) if offsets else "",
                    "implicit_start": str(offsets[2]) if offsets else "",
                    "implicit_end": str(offsets[3]) if offsets else "",
                }
            )

    print(f"Wrote to {output}")
    print("Review instructions:")
    print("  accept: YES or NO")
    print("  rejection_reason (if NO):")
    print("    generic       no specific referent")
    print("    idiom         idiomatic, not referential")
    print("    no_antecedent no recoverable entity")
    print("    not_probeable cannot write closed-form probe")
    print("    wrong_relation belongs to another category")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--instances", type=Path, default=Path("instruments/instances.csv")
    )
    parser.add_argument("--explicit-dir", type=Path, default=Path("corpus/explicit"))
    parser.add_argument("--output-dir", type=Path, default=Path("instruments"))
    args = parser.parse_args()

    generate_review_csv(
        args.instances, args.explicit_dir, args.output_dir / "o1_review.csv", "O1"
    )
    generate_review_csv(
        args.instances, args.explicit_dir, args.output_dir / "o2_review.csv", "O2"
    )


if __name__ == "__main__":
    main()
