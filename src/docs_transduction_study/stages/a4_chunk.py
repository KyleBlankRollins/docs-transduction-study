"""A4 — Fixed-size, no-overlap, character-based chunker.

Parameters: configurable chunk size, no overlap, character-based.
Chunks are written to artifacts/a4/{arm}/ preserving page paths.

Usage:
    uv run python -m docs_transduction_study.stages.a4_chunk --in-dir DIR --out DIR [--size SIZE]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"


def chunk_text(text: str, chunk_size: int) -> list[str]:
    """Split text into fixed-size, no-overlap character chunks."""
    return [
        text[i : i + chunk_size]
        for i in range(0, len(text), chunk_size)
        if text[i : i + chunk_size].strip()
    ]


def run_chunking(text_dir: Path, out_dir: Path, chunk_size: int) -> dict[str, Any]:
    """Run A4 chunking for both arms."""
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {
        "parameters": {
            "type": "character-based",
            "chunk_size": chunk_size,
            "overlap": 0,
            "justification": (
                "Fixed-size, no-overlap character-based chunking is the registered A4 "
                "definition. Character-based ensures determinism regardless of tokenizer. "
                "Size 1500 chars (~200-300 words) keeps chunks short enough to create "
                "boundary-crossing instances for H3 spans_chunks analysis."
            ),
        },
        "arms": {},
    }

    for arm in ("explicit", "implicit"):
        arm_dir = text_dir / arm
        if not arm_dir.exists():
            print(f"  WARNING: {arm_dir} not found", file=sys.stderr)
            continue

        pages = []
        for txt_path in sorted(arm_dir.rglob("*.txt")):
            if txt_path.name == "_metadata.json":
                continue
            pages.append(
                {
                    "relative_path": str(txt_path.relative_to(arm_dir)),
                    "text": txt_path.read_text(encoding="utf-8"),
                }
            )

        arm_out = out_dir / arm
        arm_out.mkdir(parents=True, exist_ok=True)
        chunk_index: list[dict] = []
        total_chunks = 0

        for page in pages:
            text = page["text"]
            chunk_size_local = chunk_size
            i = 0
            while i < len(text):
                chunk_text_val = text[i : i + chunk_size_local]
                if chunk_text_val.strip():
                    base = Path(page["relative_path"]).with_suffix("")
                    chunk_name = f"{base}-chunk-{total_chunks:04d}.txt"
                    chunk_path = arm_out / chunk_name
                    chunk_path.parent.mkdir(parents=True, exist_ok=True)
                    chunk_path.write_text(chunk_text_val, encoding="utf-8")
                    chunk_index.append(
                        {
                            "chunk_path": str(chunk_path),
                            "page": page["relative_path"],
                            "chunk_index": total_chunks,
                            "char_count": len(chunk_text_val),
                            "chunk_start": i,
                        }
                    )
                    total_chunks += 1
                i += chunk_size_local

        (arm_out / "_chunk_index.json").write_text(
            json.dumps(chunk_index, indent=2), encoding="utf-8"
        )
        results["arms"][arm] = {
            "page_count": len(pages),
            "total_chunks": total_chunks,
        }

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in-dir", type=Path, default=ARTIFACTS_DIR / "a3")
    parser.add_argument("--out", type=Path, default=ARTIFACTS_DIR / "a4")
    parser.add_argument("--size", type=int, default=1500)
    args = parser.parse_args()
    results = run_chunking(args.in_dir, args.out, args.size)
    print(f"Chunk size: {results['parameters']['chunk_size']}", file=sys.stderr)
    for arm, data in results["arms"].items():
        print(
            f"  {arm}: {data['page_count']} pages -> {data['total_chunks']} chunks",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
