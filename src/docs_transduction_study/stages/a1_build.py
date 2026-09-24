"""A1 — Two full Astro builds (explicit / implicit) with ADR-0005 overlay.

Applies the ad-pinning overlay to both trees before either build, records
Node and package-manager versions, and re-scores the spike's B2/B3/B4 checks
with the overlay in place.

Usage:
    uv run python -m docs_transduction_study.stages.a1_build [--pilot PAGE] [--out DIR]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
VENDOR_DIR = REPO_ROOT / "vendor" / "astro-docs"
OVERLAY_SRC = REPO_ROOT / "pipeline" / "overlays" / "src"
EXPLICIT_DIR = REPO_ROOT / "corpus" / "explicit"
IMPLICIT_DIR = REPO_ROOT / "corpus" / "implicit"
SPECIMENS_CSV = REPO_ROOT / "corpus" / "specimens.csv"
BUILD_DIR = REPO_ROOT / "build"
ARTIFACTS_DIR = REPO_ROOT / "artifacts"

RSYNC_EXCLUDES = ["--exclude=.git", "--exclude=node_modules"]


def _run(
    cmd: list[str], cwd: Path, *, log: Path | None = None
) -> subprocess.CompletedProcess:
    """Run a command, optionally tee stdout/stderr to a log file."""
    print(f"  running: {' '.join(cmd[:4])}... (cwd={cwd.name})", file=sys.stderr)
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if log is not None:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            f"# cmd: {' '.join(cmd)}\n# cwd: {cwd}\n# exit: {result.returncode}\n\n"
            + result.stdout
            + "\n\n--- stderr ---\n"
            + result.stderr,
        )
    if result.returncode != 0:
        stderr_lines = result.stderr.strip().splitlines()
        for line in stderr_lines[-10:]:
            print(f"    {line}", file=sys.stderr)
    return result


def _record_version_info() -> dict[str, str]:
    """Record Node, pnpm versions. Return dict for logging."""
    info = {}
    r = subprocess.run(
        ["node", "--version"], capture_output=True, text=True, check=False
    )
    info["node_version"] = r.stdout.strip() if r.returncode == 0 else "unknown"
    r = subprocess.run(
        ["pnpm", "--version"], capture_output=True, text=True, check=False
    )
    info["pnpm_version"] = r.stdout.strip() if r.returncode == 0 else "unknown"
    return info


def _apply_overlay(tree_dir: Path) -> None:
    """Apply the ADR-0005 ad-pinning overlay to a materialised tree."""
    target = tree_dir / "src" / "components" / "RightSidebar" / "RandomizedAd.astro"
    overlay_file = OVERLAY_SRC / "components" / "RightSidebar" / "RandomizedAd.astro"
    if not overlay_file.is_file():
        raise FileNotFoundError(f"ADR-0005 overlay is missing: {overlay_file}")
    if not target.is_file():
        raise FileNotFoundError(
            f"Overlay target is missing from the pinned tree: {target}"
        )
    shutil.copy2(overlay_file, target)
    print(f"  overlay applied: {target}", file=sys.stderr)


def _materialise_tree(
    tree_dir: Path, arm: str, *, pilot_page: str | None = None
) -> None:
    """Copy pinned tree + override specimen (or pilot) files."""
    print(f"\nMaterialising {arm} tree into {tree_dir}...", file=sys.stderr)
    if tree_dir.exists():
        shutil.rmtree(tree_dir)
    tree_dir.mkdir(parents=True)
    shutil.copytree(
        VENDOR_DIR,
        tree_dir,
        symlinks=True,
        ignore=shutil.ignore_patterns(".git", "node_modules", "dist", ".astro"),
        dirs_exist_ok=True,
    )
    _apply_overlay(tree_dir)
    print(f"  installing deps in {tree_dir.name}...", file=sys.stderr)
    result = _run(
        ["pnpm", "install", "--frozen-lockfile", "--prefer-offline"],
        cwd=tree_dir,
        log=BUILD_DIR / f"logs/pnpm-install-{arm}.log",
    )
    if result.returncode != 0:
        print(f"  pnpm install failed for {arm}", file=sys.stderr)
        sys.exit(1)
    if pilot_page:
        _override_pilot(tree_dir, arm, pilot_page)
    else:
        _override_specimens(tree_dir, arm)


def _override_specimens(tree_dir: Path, arm: str) -> None:
    """Copy specimen files from corpus/{arm}/ into the build tree."""
    source_dir = EXPLICIT_DIR if arm == "explicit" else IMPLICIT_DIR
    dst_base = tree_dir / "src" / "content" / "docs" / "en"
    with SPECIMENS_CSV.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            source_path = row["source_path"]
            src_file = source_dir / source_path
            dst_file = dst_base / source_path
            if not src_file.is_file():
                raise FileNotFoundError(f"Specimen source is missing: {src_file}")
            if not dst_file.is_file():
                raise FileNotFoundError(
                    f"Specimen route is missing from the pinned tree: {dst_file}"
                )
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)


def _override_pilot(tree_dir: Path, arm: str, pilot_src: str) -> None:
    """Copy the pilot page into the build tree (disposable).

    For the implicit arm, uses the de-marked copy from /tmp/pilot/
    (created by the Makefile's demark step before calling A1).
    For the explicit arm, uses the vendor source.
    """
    dst_base = tree_dir / "src" / "content" / "docs" / "en"
    rel = Path(pilot_src).name

    if arm == "implicit":
        implicit_src = Path(f"/tmp/pilot/{rel.replace('.mdx', '-implicit.mdx')}")
        if implicit_src.exists():
            dst_file = dst_base / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(implicit_src, dst_file)
            print(f"  pilot (implicit): {implicit_src}", file=sys.stderr)
            return
        raise FileNotFoundError(f"De-marked implicit pilot is missing: {implicit_src}")

    # Explicit arm (or fallback if no implicit copy found)
    candidates = [
        VENDOR_DIR / "src" / "content" / "docs" / "en" / pilot_src,
        EXPLICIT_DIR / pilot_src,
    ]
    src_file: Path | None = None
    for c in candidates:
        if c.exists():
            src_file = c
            break
    if src_file is None:
        print(f"  ERROR: pilot page not found: {pilot_src}", file=sys.stderr)
        sys.exit(1)
    dst_file = dst_base / rel
    dst_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_file, dst_file)
    print(f"  pilot (explicit): {dst_file}", file=sys.stderr)
    shutil.copy2(src_file, dst_file)
    print(f"  pilot: {dst_file}", file=sys.stderr)


def _build(tree_dir: Path, arm: str) -> int:
    """Run pnpm build. Returns exit code."""
    print(f"\nBuilding {arm} arm in {tree_dir}...", file=sys.stderr)
    log = BUILD_DIR / f"logs/build-{arm}.log"
    result = _run(["pnpm", "build"], cwd=tree_dir, log=log)
    return result.returncode


def _copy_artifacts(
    arm: str, tree_dir: Path, out_dir: Path, *, pilot_page: str | None = None
) -> int:
    """Copy built HTML from tree_dir/dist/ into artifacts/{arm}/."""
    dist = tree_dir / "dist"
    if pilot_page is not None:
        page_path = Path(pilot_page)
        if page_path.is_absolute() or ".." in page_path.parts:
            raise ValueError("Pilot page must be relative to the English docs root")
        relative_html = Path("en") / page_path.with_suffix("") / "index.html"
        source = dist / relative_html
        if not source.is_file():
            raise FileNotFoundError(f"Expected compiled pilot HTML not found: {source}")
        target = out_dir / arm
        shutil.rmtree(target, ignore_errors=True)
        destination = target / relative_html
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        print(f"  Copied pilot HTML only to {destination}", file=sys.stderr)
        return 1
    if not dist.exists():
        print(f"  No dist/ found for {arm}", file=sys.stderr)
        return 0
    target = out_dir / arm
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(dist, target)
    n = len(list(target.rglob("*.html")))
    print(f"  Copied {n} HTML files to {target}", file=sys.stderr)
    return n


def _check_determinism(out_dir: Path, arm: str) -> list[str]:
    """Build the same tree twice and diff. Returns list of differing paths."""
    print(f"\n--- B2 determinism check ({arm}) ---", file=sys.stderr)
    build_a = out_dir / f"determinism-{arm}-a"
    build_b = out_dir / f"determinism-{arm}-b"
    shutil.rmtree(build_a, ignore_errors=True)
    shutil.rmtree(build_b, ignore_errors=True)
    _materialise_tree(build_a, arm)
    _build(build_a, arm)
    _materialise_tree(build_b, arm)
    _build(build_b, arm)
    differing: list[str] = []
    html_files_a = sorted(build_a.rglob("*.html"))
    set_a = {str(p.relative_to(build_a)) for p in html_files_a}
    html_files_b = sorted(build_b.rglob("*.html"))
    set_b = {str(p.relative_to(build_b)) for p in html_files_b}
    for rel in sorted(set_a | set_b):
        fa = build_a / rel if (build_a / rel).exists() else None
        fb = build_b / rel if (build_b / rel).exists() else None
        if fa and fb:
            if fa.read_bytes() != fb.read_bytes():
                differing.append(str(rel))
        else:
            differing.append(f"{rel} (exists in one build only)")
    shutil.rmtree(build_a, ignore_errors=True)
    shutil.rmtree(build_b, ignore_errors=True)
    return differing


def _b3_b4_extraction_check(out_dir: Path, arm: str) -> None:
    """B3/B4 — verify extraction target and chrome fraction."""
    print(f"\n--- B3/B4 extraction check ({arm}) ---", file=sys.stderr)
    from bs4 import BeautifulSoup

    from docs_transduction_study.stages.a3_extract import extract_article_text

    tree = out_dir / f"chrome-check-{arm}"
    shutil.rmtree(tree, ignore_errors=True)
    _materialise_tree(tree, arm)
    _build(tree, arm)
    dist = tree / "dist"
    pages = sorted(dist.rglob("*.html"))[:50]
    total_chars = article_chars = chrome_chars = 0
    for page in pages:
        html = page.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")
        article_text, _ = extract_article_text(page)
        body = soup.find("body")
        body_text = body.get_text(separator=" ") if body else ""
        total_chars += len(body_text)
        article_chars += len(article_text)
        chrome_chars += len(body_text) - len(article_text)
    shutil.rmtree(tree, ignore_errors=True)
    if total_chars == 0:
        print("  WARNING: no text found", file=sys.stderr)
        return
    chrome_pct = (chrome_chars / total_chars) * 100
    print(
        f"  Article: {article_chars:,} chars ({(article_chars / total_chars) * 100:.1f}%)",
        file=sys.stderr,
    )
    print(f"  Chrome:  {chrome_chars:,} chars ({chrome_pct:.1f}%)", file=sys.stderr)
    print(f"  Pages sampled: {len(pages)}", file=sys.stderr)


def _html_checksums(dist: Path) -> dict[str, str]:
    checksums = {
        path.relative_to(dist).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(dist.rglob("*.html"))
    }
    if not checksums:
        raise ValueError("Determinism requires nonempty compiled HTML output")
    return checksums


def _pilot_chrome_metrics(
    html: str, text: str, chunk_size: int = 1500
) -> dict[str, Any]:
    from bs4 import BeautifulSoup

    content = BeautifulSoup(html, "html.parser").select_one(".sl-markdown-content")
    if content is None:
        raise ValueError("Pilot chrome assessment requires the extraction container")
    labels = [
        re.sub(r"\s+", " ", element.get_text(separator=" ")).strip()
        for element in content.select(
            ".sl-anchor-link .sr-only, .expressive-code figcaption.header .sr-only"
        )
    ]
    spans: list[tuple[int, int]] = []
    for label in set(labels):
        if not label:
            continue
        matches = list(re.finditer(re.escape(label), text))
        if len(matches) != labels.count(label):
            raise ValueError(
                "Generated chrome text is ambiguous in extracted pilot text"
            )
        spans.extend((match.start(), match.end()) for match in matches)
    chunk_fractions = [
        sum(
            max(0, min(end, offset + chunk_size) - max(start, offset))
            for start, end in spans
        )
        / len(text[offset : offset + chunk_size])
        for offset in range(0, len(text), chunk_size)
    ]
    return {
        "identified_labels": len(labels),
        "identified_chrome_chars": sum(end - start for start, end in spans),
        "identified_chrome_fraction": sum(end - start for start, end in spans)
        / len(text),
        "chunk_fractions": chunk_fractions,
        "scope": "Generated heading-anchor and code-window labels; tab labels retained as relational evidence",
    }


def _verify_pilot_page(tree: Path, pilot_page: str, out_dir: Path) -> dict[str, Any]:
    from bs4 import BeautifulSoup

    from docs_transduction_study import anchors
    from docs_transduction_study.stages.a2_snapshot import run_snapshot
    from docs_transduction_study.stages.a3_extract import extract_article_text
    from docs_transduction_study.stages.a4_chunk import chunk_text

    route = f"/en/{Path(pilot_page).with_suffix('').as_posix()}/"
    page = tree / "dist" / route.lstrip("/") / "index.html"
    text, metadata = extract_article_text(page)
    soup = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
    content = soup.select_one(".sl-markdown-content")
    assert content is not None
    body = soup.find("body")
    assert body is not None
    body_text = re.sub(r"\s+", " ", body.get_text(separator=" ")).strip()
    chunks = chunk_text(text, 1500)
    if "".join(chunks) != text:
        raise ValueError("Pilot chunks do not reconstruct extracted text")
    chunk_index = [
        {
            "chunk_start": offset,
            "char_count": len(text[offset : offset + 1500]),
            "chunk_index": offset // 1500,
        }
        for offset in range(0, len(text), 1500)
    ]
    resolved = []
    for paragraph in content.find_all("p")[:3]:
        passage = re.sub(r"\s+", " ", paragraph.get_text(separator=" ")).strip()
        offset = anchors.resolve_anchor_offset(passage, text)
        if offset is None:
            raise ValueError("Pilot paragraph anchor did not resolve")
        chunk = anchors.find_chunk_for_offset(offset, chunk_index)
        if chunk is None:
            raise ValueError("Pilot paragraph has no assigned chunk")
        resolved.append(
            {
                "offset": offset,
                "chunk_index": chunk["chunk_index"],
                "spans_chunks": anchors.compute_spans_chunks(
                    passage, text, chunk_index
                ),
            }
        )
    snapshots = run_snapshot(tree / "dist", route, out_dir=out_dir)
    if not snapshots.get("stable"):
        raise ValueError(f"Pilot A2 snapshots unstable or unavailable: {snapshots}")
    return {
        "extraction": metadata,
        "body_chars": len(body_text),
        "content_chars": len(text),
        "outside_content_chars": len(body_text) - len(text),
        "structural_chrome_inside": len(content.select("nav,header,footer")),
        "generated_chrome": _pilot_chrome_metrics(
            page.read_text(encoding="utf-8"), text
        ),
        "tab_panels_html": len(content.select('[role="tabpanel"]')),
        "hidden_tab_panels_html": len(content.select('[role="tabpanel"][hidden]')),
        "chunks": len(chunks),
        "chunk_reconstruction": True,
        "paragraph_anchor_checks": resolved,
        "a2": snapshots,
    }


def run_builds(
    out_dir: Path,
    *,
    pilot_page: str | None = None,
    skip_determinism: bool = False,
    skip_chrome: bool = False,
    verify_pilot: bool = False,
) -> dict[str, Any]:
    """Run the A1 stage: materialise, overlay, build both arms.

    Returns a dict with results for runlog recording.
    """
    from docs_transduction_study.seed import _instrument_locked

    if verify_pilot and pilot_page is None:
        raise ValueError("Pilot verification requires a pilot page")
    if pilot_page is None and not _instrument_locked(REPO_ROOT / "DESIGN.md"):
        raise ValueError("Study artifact generation is forbidden before L2")
    if pilot_page is not None:
        with SPECIMENS_CSV.open(encoding="utf-8", newline="") as handle:
            if any(row["source_path"] == pilot_page for row in csv.DictReader(handle)):
                raise ValueError("Pilot page must not be a study specimen")
        if not skip_determinism or not skip_chrome:
            raise ValueError("Pilot builds require isolated pilot-only checks")
    out_dir.mkdir(parents=True, exist_ok=True)
    versions = _record_version_info()
    print(
        f"Node: {versions['node_version']}, pnpm: {versions['pnpm_version']}",
        file=sys.stderr,
    )

    results: dict[str, Any] = {
        "versions": versions,
        "build_exit_codes": {},
        "pages_copied": {},
    }
    explicit_checksums: dict[str, str] = {}

    for arm in ("explicit", "implicit"):
        if pilot_page is not None:
            with tempfile.TemporaryDirectory(prefix=f"study-pilot-{arm}-") as temporary:
                tree = Path(temporary) / "tree"
                _materialise_tree(tree, arm, pilot_page=pilot_page)
                rc = _build(tree, arm)
                results["build_exit_codes"][arm] = rc
                if rc != 0:
                    raise RuntimeError(f"Pilot {arm} build failed with exit code {rc}")
                results["pages_copied"][arm] = _copy_artifacts(
                    arm, tree, out_dir / "artifacts", pilot_page=pilot_page
                )
                if verify_pilot:
                    results.setdefault("pilot_checks", {})[arm] = _verify_pilot_page(
                        tree, pilot_page, out_dir / "a2" / arm
                    )
                    if arm == "explicit":
                        explicit_checksums = _html_checksums(tree / "dist")
            continue
        tree = out_dir / "trees" / arm
        _materialise_tree(tree, arm, pilot_page=pilot_page)
        rc = _build(tree, arm)
        results["build_exit_codes"][arm] = rc
        if rc == 0:
            n = _copy_artifacts(arm, tree, out_dir / "artifacts", pilot_page=pilot_page)
            results["pages_copied"][arm] = n

    if verify_pilot:
        with tempfile.TemporaryDirectory(prefix="study-pilot-repeat-") as temporary:
            tree = Path(temporary) / "tree"
            _materialise_tree(tree, "explicit", pilot_page=pilot_page)
            if _build(tree, "explicit-repeat") != 0:
                raise RuntimeError("Repeated explicit pilot build failed")
            repeated = _html_checksums(tree / "dist")
        differences = sorted(
            path
            for path in explicit_checksums.keys() | repeated.keys()
            if explicit_checksums.get(path) != repeated.get(path)
        )
        results["determinism_pages"] = len(explicit_checksums)
        results["determinism_differing"] = differences
        results["determinism_pass"] = not differences
        (out_dir / "verification.json").write_text(
            json.dumps(results, indent=2), encoding="utf-8"
        )
        if differences:
            raise ValueError(
                f"Pilot build nondeterminism: {len(differences)} differing HTML files"
            )

    # Determinism check (B2)
    if not skip_determinism:
        differing = _check_determinism(out_dir, "explicit")
        results["determinism_differing"] = differing
        results["determinism_pass"] = len(differing) == 0
        if differing:
            print(f"  B2: {len(differing)} differing file(s)", file=sys.stderr)

    # B3/B4 chrome check
    if not skip_chrome:
        _b3_b4_extraction_check(out_dir, "explicit")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=ARTIFACTS_DIR / "a1",
        help="Output directory for build trees and logs",
    )
    parser.add_argument(
        "--pilot",
        type=str,
        default=None,
        help="Relative path to pilot page (disposable)",
    )
    parser.add_argument(
        "--skip-determinism",
        action="store_true",
        help="Skip the B2 determinism comparison",
    )
    parser.add_argument(
        "--skip-chrome", action="store_true", help="Skip the B3/B4 chrome check"
    )
    parser.add_argument(
        "--pilot-only",
        action="store_true",
        help="Process only the pilot page; skip B2/B3/B4 and specimen materialisation",
    )
    parser.add_argument("--verify-pilot", action="store_true")
    args = parser.parse_args()
    if args.pilot_only and not args.pilot:
        parser.error("--pilot-only requires --pilot")

    results = run_builds(
        args.out,
        pilot_page=args.pilot,
        skip_determinism=args.skip_determinism or args.pilot_only,
        skip_chrome=args.skip_chrome or args.pilot_only,
        verify_pilot=args.verify_pilot,
    )

    rc_explicit = results["build_exit_codes"]["explicit"]
    rc_implicit = results["build_exit_codes"]["implicit"]
    print(f"\n{'=' * 50}", file=sys.stderr)
    print(f"Explicit build: exit {rc_explicit}", file=sys.stderr)
    print(f"Implicit build: exit {rc_implicit}", file=sys.stderr)
    if "determinism_pass" in results:
        print(
            f"B2 determinism: {'PASS' if results['determinism_pass'] else 'FAIL'} "
            f"({len(results.get('determinism_differing', []))} differing)",
            file=sys.stderr,
        )

    if rc_explicit != 0 or rc_implicit != 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
