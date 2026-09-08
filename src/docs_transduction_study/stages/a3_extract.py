"""A3 — Named, versioned extractor in plain-text mode, article element only.

Extracts text from the <article> element using BeautifulSoup (version recorded).
Output is plain text with no structure preserved. Raises ValueError if no
<article> element is found — the registered target is article-only, with no
fallback to <main> or <body> (which would introduce theme chrome).

Usage:
    uv run python -m docs_transduction_study.stages.a3_extract [--artifacts DIR] [--out DIR]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"


def extract_article_text(html_path: Path) -> tuple[str, dict]:
    """Extract plain text from the <article> element.

    Raises ValueError if no <article> is found — the registered extraction
    target is article-only with no fallback. Fallback would introduce theme
    chrome into A3 artifacts.
    """
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article")
    if article is None:
        raise ValueError(
            f"No <article> element in {html_path}. A3 requires article-only extraction."
        )
    text = re.sub(r"\s+", " ", article.get_text(separator=" ")).strip()
    return text, {
        "html_path": str(html_path),
        "extractor_name": EXTRACTOR_NAME,
        "extractor_version": EXTRACTOR_VERSION,
        "extraction_target": "article",
        "output_mode": OUTPUT_MODE,
        "char_count": len(text),
    }


def run_extraction(artifacts_in: Path, out_dir: Path) -> dict[str, Any]:
    """Run A3 extraction for both arms. Raises on first extraction failure."""
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {
        "extractor": {
            "name": EXTRACTOR_NAME,
            "version": EXTRACTOR_VERSION,
            "target": EXTRACTION_TARGET,
            "output_mode": OUTPUT_MODE,
        },
        "arms": {},
    }

    for arm in ("explicit", "implicit"):
        arm_dir = artifacts_in / arm
        if not arm_dir.exists():
            print(f"  WARNING: {arm_dir} not found", file=sys.stderr)
            continue

        arm_out = out_dir / arm
        arm_out.mkdir(parents=True, exist_ok=True)
        metadata_list: list[dict] = []
        total_chars = 0
        n_pages = 0

        for html_path in sorted(arm_dir.rglob("*.html")):
            text, meta = extract_article_text(html_path)
            rel = html_path.relative_to(arm_dir)
            txt_path = arm_out / rel.with_suffix(".txt")
            txt_path.parent.mkdir(parents=True, exist_ok=True)
            txt_path.write_text(text, encoding="utf-8")
            meta["relative_path"] = str(rel)
            metadata_list.append(meta)
            total_chars += len(text)
            n_pages += 1

        with open(arm_out / "_metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata_list, f, indent=2)
        results["arms"][arm] = {
            "page_count": n_pages,
            "total_chars": total_chars,
            "avg_chars": total_chars / n_pages if n_pages else 0,
        }

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts", type=Path, default=ARTIFACTS_DIR / "a1" / "artifacts"
    )
    parser.add_argument("--out", type=Path, default=ARTIFACTS_DIR / "a3")
    args = parser.parse_args()
    results = run_extraction(args.artifacts, args.out)
    for arm, data in results["arms"].items():
        print(
            f"  {arm}: {data['page_count']} pages, {data['total_chars']:,} chars",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()

EXTRACTOR_NAME = "BeautifulSoup"
EXTRACTOR_VERSION = "4.15.0"
EXTRACTION_TARGET = "article element only (<article>)"
OUTPUT_MODE = "plain text (get_text with separator=' ')"
