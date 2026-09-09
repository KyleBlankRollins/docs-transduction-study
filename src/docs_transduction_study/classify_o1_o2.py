"""Mechanical O1/O2 classifier — pre-fills accept/rejection_reason for obvious noise."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

# Idioms — expressions that are almost always idiomatic, not referential
_IDIOM_EXPRESSIONS: set[str] = {
    "the same time",
    "the same way",
    "the meantime",
    "the other hand",
    "the same",
    "the same page",
    "the same direction",
    "the same thing",
    "the other",
    "the rest",
    "the end",
    "the beginning",
    "the first place",
    "the long run",
    "the long term",
    "the short term",
    "the future",
    "the past",
    "the present",
    "the moment",
    "the case",
    "the time",
    "the way",
    "the above",
    "the below",
    "the following",
}

# Generic — no specific recoverable referent
_GENERIC_EXPRESSIONS: set[str] = {
    "the community",
    "the page",
    "the site",
    "the website",
    "the documentation",
    "the docs",
    "the guide",
    "the tutorial",
    "the article",
    "the internet",
    "the web",
    "the world",
    "the user",
    "the developer",
    "the reader",
    "the audience",
    "the entry",
    "the file",
    "the directory",
    "the folder",
    "the path",
    "the command",
    "the terminal",
    "the code",
    "the script",
    "the function",
    "the method",
    "the class",
    "the object",
    "the variable",
    "the value",
    "the string",
    "the number",
    "the type",
    "the name",
    "the id",
    "the key",
    "the option",
    "the setting",
    "the configuration",
    "the default",
    "the output",
    "the input",
    "the content",
    "the text",
    "your choice",
    "your needs",
    "your preference",
    "your project settings",
}


def _lower_normalize(expr: str) -> str:
    return expr.strip().lower()


def _check_code_context(before: str, after: str) -> bool:
    """True if expression is inside a code block."""
    return "```" in (before + after)


def classify_o1(row: dict[str, str]) -> tuple[str, str, str]:
    """Classify an O1 candidate. Returns (accept, rejection_reason, note)."""
    expr = row.get("expression", "")
    ctx_before = row.get("context_before", "")
    ctx_after = row.get("context_after", "")
    norm = _lower_normalize(expr)

    # Idiom check
    for idiom in _IDIOM_EXPRESSIONS:
        if idiom in norm:
            return "NO", "idiom", f"Mechanical: '{idiom}' is idiomatic"

    # Generic check (exact match to avoid false positives)
    for generic in _GENERIC_EXPRESSIONS:
        if norm == generic:
            return "NO", "generic", f"Mechanical: '{generic}' has no specific referent"

    # Fragment check: very short incomplete reference
    words = norm.split()
    if len(words) <= 2:
        return (
            "NO",
            "generic",
            f"Mechanical: '{expr}' is a fragment, not a complete reference",
        )

    # Code context check
    if _check_code_context(ctx_before, ctx_after):
        return (
            "NO",
            "not_probeable",
            f"Mechanical: '{expr}' appears inside a code block",
        )

    # No mechanical decision
    return "", "", ""


def classify_o2(row: dict[str, str]) -> tuple[str, str, str]:
    """Classify an O2 candidate mechanically."""
    ctx_before = row.get("context_before", "")
    ctx_after = row.get("context_after", "")
    if _check_code_context(ctx_before, ctx_after):
        return (
            "NO",
            "not_probeable",
            (f"Mechanical: '{row.get('expression', '')}' appears inside a code block"),
        )
    return "", "", ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--o1-review", type=Path, default=Path("instruments/o1_review.csv")
    )
    parser.add_argument(
        "--o2-review", type=Path, default=Path("instruments/o2_review.csv")
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    rejections = {
        "O1": {"idiom": 0, "generic": 0, "not_probeable": 0},
        "O2": {"idiom": 0, "generic": 0, "not_probeable": 0},
    }

    for file_key, review_path, classify_fn in [
        ("O1", args.o1_review, classify_o1),
        ("O2", args.o2_review, classify_o2),
    ]:
        if not review_path.exists():
            print(f"{review_path} not found, skipping {file_key}")
            continue

        with review_path.open("r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        out_path = (
            Path(args.output_dir) / review_path.name if args.output_dir else review_path
        )
        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=list(rows[0].keys()), lineterminator="\n"
            )
            writer.writeheader()
            for row in rows:
                if not row.get("accept"):
                    accept, reason, _note = classify_fn(row)
                    if accept:
                        row["accept"] = accept
                        row["rejection_reason"] = reason
                        rejections[file_key][reason] = (
                            rejections[file_key].get(reason, 0) + 1
                        )
                writer.writerow(row)

    print("Mechanical classification complete.")
    print("Rejection summary:")
    for rt in ["O1", "O2"]:
        total = sum(rejections[rt].values())
        if total:
            print(f"  {rt}: {total} rejected")
            for reason, count in sorted(rejections[rt].items()):
                if count:
                    print(f"    {reason}: {count}")

    print()
    print("Entries left blank for non-obvious cases need human review.")
    print("Edit the review CSV accept/rejection_reason columns.")


if __name__ == "__main__":
    main()
