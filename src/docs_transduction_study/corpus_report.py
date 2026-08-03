"""Build the W1 component-usage report for the pinned Astro corpus."""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SOURCE_ROOT = Path("vendor/astro-docs/src/content/docs/en")
DEFAULT_OUTPUT = Path("corpus/component-counts.csv")
SUPPORTED_SUFFIXES = {".md", ".mdx"}
NORMATIVE_KEYWORDS = ("MUST", "SHOULD", "MAY", "REQUIRED", "SHALL")

_COMPONENT_PATTERNS = {
    "steps_count": re.compile(r"<Steps\b", re.IGNORECASE),
    # Raw Starlight <Tabs> plus the corpus's custom wrapper family, which is
    # the dominant tab idiom (~100 en pages; runlog 2026-08-02).
    "tabs_count": re.compile(
        r"<(?:Tabs|PackageManagerTabs|UIFrameworkTabs|AstroVueTabs"
        r"|StaticSsrTabs|JavascriptFlavorTabs|AstroJSXTabs)\b",
        re.IGNORECASE,
    ),
    "aside_count": re.compile(
        r"(?:^|\n)\s*:::(?:note|tip|caution|danger)\b|<Aside\b",
        re.IGNORECASE,
    ),
    # R4 selection heuristic: the corpus marks preconditions with
    # "Prerequisites"/"Requirements" headings (dominant idiom) and with
    # titled asides (:::note[Prerequisites]). Titled asides also appear in
    # aside_count; columns are signals, not a partition.
    "prereq_count": re.compile(
        r"^#{2,4} .*\b(?:Prerequisites?|Requirements?)\b"
        r"|:::(?:note|caution|tip)\[[^\]\n]*Prerequisite",
        re.IGNORECASE | re.MULTILINE,
    ),
}
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEPARATOR = re.compile(r"^\s*\|\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|\s*$")


@dataclass(frozen=True)
class PageCounts:
    source_path: str
    steps_count: int
    tabs_count: int
    aside_count: int
    prereq_count: int
    tables_count: int
    normative_keywords_count: int


def _count_tables(lines: list[str]) -> int:
    """Count Markdown tables by their header/separator pair."""
    return sum(
        _TABLE_ROW.match(lines[index]) is not None
        and index + 1 < len(lines)
        and _TABLE_SEPARATOR.match(lines[index + 1]) is not None
        for index in range(len(lines) - 1)
    )


def count_page(path: Path, relative_to: Path) -> PageCounts:
    text = path.read_text(encoding="utf-8")
    keyword_pattern = re.compile(
        r"(?<![A-Za-z])(?:" + "|".join(NORMATIVE_KEYWORDS) + r")(?![A-Za-z])"
    )
    counts = {
        name: len(pattern.findall(text))
        for name, pattern in _COMPONENT_PATTERNS.items()
    }
    return PageCounts(
        source_path=path.relative_to(relative_to).as_posix(),
        **counts,
        tables_count=_count_tables(text.splitlines()),
        normative_keywords_count=len(keyword_pattern.findall(text)),
    )


def scan_corpus(source_root: Path = DEFAULT_SOURCE_ROOT) -> list[PageCounts]:
    if not source_root.is_dir():
        raise FileNotFoundError(f"English docs directory does not exist: {source_root}")
    pages = sorted(
        path
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    return [count_page(path, source_root) for path in pages]


def write_report(rows: list[PageCounts], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_path",
        "steps_count",
        "tabs_count",
        "aside_count",
        "prereq_count",
        "tables_count",
        "normative_keywords_count",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(row.__dict__ for row in rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rows = scan_corpus(args.source_root)
    write_report(rows, args.output)
    print(f"Wrote {len(rows)} pages to {args.output}")


if __name__ == "__main__":
    main()
