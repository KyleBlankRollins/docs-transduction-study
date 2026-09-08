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
import shutil
import subprocess
import sys
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
    if overlay_file.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(overlay_file, target)
        print(f"  overlay applied: {target}", file=sys.stderr)
    else:
        print(f"  WARNING: overlay file not found at {overlay_file}", file=sys.stderr)


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
        ignore=shutil.ignore_patterns(".git", "node_modules"),
        dirs_exist_ok=True,
    )
    _apply_overlay(tree_dir)
    print(f"  installing deps in {tree_dir.name}...", file=sys.stderr)
    result = _run(
        ["pnpm", "install", "--prefer-offline"],
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
            if not src_file.exists():
                print(f"  WARNING: {src_file} not found, skipping", file=sys.stderr)
                continue
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


def _copy_artifacts(arm: str, tree_dir: Path, out_dir: Path) -> int:
    """Copy built HTML from tree_dir/dist/ into artifacts/{arm}/."""
    dist = tree_dir / "dist"
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
        article = soup.find("article") or soup.find("main") or soup.find("body")
        article_text = article.get_text(separator=" ") if article else ""
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


def run_builds(
    out_dir: Path,
    *,
    pilot_page: str | None = None,
    skip_determinism: bool = False,
    skip_chrome: bool = False,
) -> dict[str, Any]:
    """Run the A1 stage: materialise, overlay, build both arms.

    Returns a dict with results for runlog recording.
    """
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

    for arm in ("explicit", "implicit"):
        tree = out_dir / "trees" / arm
        _materialise_tree(tree, arm, pilot_page=pilot_page)
        rc = _build(tree, arm)
        results["build_exit_codes"][arm] = rc
        if rc == 0:
            n = _copy_artifacts(arm, tree, out_dir / "artifacts")
            results["pages_copied"][arm] = n

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
    args = parser.parse_args()

    results = run_builds(
        args.out,
        pilot_page=args.pilot,
        skip_determinism=args.skip_determinism or args.pilot_only,
        skip_chrome=args.skip_chrome or args.pilot_only,
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
