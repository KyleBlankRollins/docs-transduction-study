"""A3 — Plain-text extraction from the amended content-container selector.

Extracts exactly one .sl-markdown-content element using BeautifulSoup.
No fallback to article, main, or body is allowed (amendment A4).

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

import bs4
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
EXTRACTOR_NAME = "BeautifulSoup"
EXTRACTOR_VERSION = bs4.__version__
EXTRACTION_TARGET = ".sl-markdown-content"
OUTPUT_MODE = "plain text (get_text with separator=' ')"


def extract_article_text(html_path: Path) -> tuple[str, dict]:
    """Extract the single registered content container, without a fallback."""
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    containers = soup.select(EXTRACTION_TARGET)
    if len(containers) != 1:
        raise ValueError(
            f"Expected exactly one {EXTRACTION_TARGET} element in {html_path}; "
            f"found {len(containers)}. A3 has no fallback."
        )
    text = re.sub(r"\s+", " ", containers[0].get_text(separator=" ")).strip()
    if not text:
        raise ValueError(f"Empty content container in {html_path}")
    return text, {
        "html_path": str(html_path),
        "extractor_name": EXTRACTOR_NAME,
        "extractor_version": EXTRACTOR_VERSION,
        "extraction_target": EXTRACTION_TARGET,
        "output_mode": OUTPUT_MODE,
        "char_count": len(text),
    }


def run_extraction(artifacts_in: Path, out_dir: Path) -> dict[str, Any]:
    """Run A3 extraction for both arms. Raises on first extraction failure."""
    page_sets = {
        arm: {
            page.relative_to(artifacts_in / arm)
            for page in (artifacts_in / arm).rglob("*.html")
        }
        for arm in ("explicit", "implicit")
    }
    if not page_sets["explicit"] or page_sets["explicit"] != page_sets["implicit"]:
        raise ValueError("A3 requires nonempty, matching page sets in both arms")
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
