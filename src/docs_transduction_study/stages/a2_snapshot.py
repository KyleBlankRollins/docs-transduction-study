"""A2 — Playwright accessibility snapshot of the served page.

Default page state, no interaction. Snapshots the pilot page twice and diffs
to verify tree stability across loads.

Usage:
    uv run python -m docs_transduction_study.stages.a2_snapshot --tree-dir DIR
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"


def _get_snapshot(port: int, path: str) -> dict | None:
    """Use Playwright to get the accessibility tree of a page."""
    from playwright.sync_api import sync_playwright

    url = f"http://localhost:{port}{path}"
    print(f"  fetching: {url}", file=sys.stderr)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1000)
        snapshot = page.accessibility.snapshot()  # type: ignore[attr-defined]
        browser.close()
    return snapshot


def _diff_snapshots(a: dict, b: dict, path: str = "") -> list[str]:
    """Recursively diff two accessibility snapshots."""
    diffs: list[str] = []
    for key in sorted(set(a.keys()) | set(b.keys())):
        subpath = f"{path}.{key}" if path else key
        va = a.get(key)
        vb = b.get(key)
        if key == "children" and isinstance(va, list) and isinstance(vb, list):
            for i, (ca, cb) in enumerate(zip(va, vb)):
                if ca.get("role") != cb.get("role") or ca.get("name") != cb.get("name"):
                    diffs.append(f"{subpath}[{i}] role/name differ")
            if len(va) != len(vb):
                diffs.append(f"{subpath}: child count {len(va)} vs {len(vb)}")
        elif isinstance(va, dict) and isinstance(vb, dict):
            diffs.extend(_diff_snapshots(va, vb, subpath))
        elif va != vb:
            diffs.append(f"{subpath}: {va!r} != {vb!r}")
    return diffs


def _flatten_a11y_tree(node: dict, depth: int = 0) -> list[tuple[int, str, str]]:
    """Flatten accessibility tree into (depth, role, name) tuples."""
    rows: list[tuple[int, str, str]] = []
    role = node.get("role", "(unknown)")
    name = node.get("name", "")
    rows.append((depth, role, name))
    for child in node.get("children", []):
        if isinstance(child, dict):
            rows.extend(_flatten_a11y_tree(child, depth + 1))
    return rows


def _start_dev_server(tree_dir: Path, port: int) -> subprocess.Popen:
    """Start the Astro dev server. Returns process handle."""
    log = ARTIFACTS_DIR / "a2" / "server.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "w") as logf:
        proc = subprocess.Popen(
            ["pnpm", "dev", "--port", str(port), "--host"],
            cwd=tree_dir,
            stdout=logf,
            stderr=subprocess.STDOUT,
            # type: ignore[arg-type]
        )
    import urllib.error
    import urllib.request

    for _ in range(30):
        try:
            urllib.request.urlopen(f"http://localhost:{port}", timeout=2)
            return proc
        except urllib.error.URLError, ConnectionError:
            time.sleep(1)
    print("ERROR: dev server did not start within 30s", file=sys.stderr)
    proc.terminate()
    sys.exit(1)


def run_snapshot(
    tree_dir: Path, page_path: str, port: int = 4321, out_dir: Path | None = None
) -> dict[str, Any]:
    """Snapshot the served page's accessibility tree twice. Returns results."""
    if out_dir is None:
        out_dir = ARTIFACTS_DIR / "a2"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Starting dev server on port {port}...", file=sys.stderr)
    proc = _start_dev_server(tree_dir, port)

    try:
        snap1 = _get_snapshot(port, page_path)
        if snap1 is None:
            return {"error": "snapshot returned None"}
        snap2 = _get_snapshot(port, page_path)
        if snap2 is None:
            return {"error": "snapshot 2 returned None"}

        rows1 = _flatten_a11y_tree(snap1)
        rows2 = _flatten_a11y_tree(snap2)

        (out_dir / "snapshot-1.json").write_text(
            json.dumps(snap1, indent=2), encoding="utf-8"
        )
        (out_dir / "snapshot-2.json").write_text(
            json.dumps(snap2, indent=2), encoding="utf-8"
        )

        def _rows_to_text(rows: list) -> str:
            lines = []
            for d, r, n in rows:
                lines.append(f"{'  ' * d}{r}: {n}" if n else f"{'  ' * d}{r}")
            return "\n".join(lines)

        (out_dir / "snapshot-1.txt").write_text(_rows_to_text(rows1), encoding="utf-8")
        (out_dir / "snapshot-2.txt").write_text(_rows_to_text(rows2), encoding="utf-8")

        diffs = _diff_snapshots(snap1, snap2)
        tab_details = [
            {"depth": d, "role": r, "name": n}
            for d, r, n in rows1
            if r in ("tablist", "tab", "tabpanel")
        ]

        return {
            "page_path": page_path,
            "snapshot_count": 2,
            "diffs": diffs,
            "stable": len(diffs) == 0,
            "tab_roles_found": len(tab_details) > 0,
            "tab_details": tab_details,
            "total_nodes_snap1": len(rows1),
            "total_nodes_snap2": len(rows2),
        }
    finally:
        proc.terminate()
        proc.wait(timeout=10)
        print("Dev server stopped.", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree-dir", type=Path, required=True)
    parser.add_argument("--page", type=str, default="/en/install-and-setup/")
    parser.add_argument("--port", type=int, default=4321)
    parser.add_argument("--out", type=Path, default=ARTIFACTS_DIR / "a2")
    args = parser.parse_args()
    results = run_snapshot(args.tree_dir, args.page, args.port, args.out)
    if "error" in results:
        print(f"ERROR: {results['error']}", file=sys.stderr)
        sys.exit(1)
    print(f"\nStable: {results['stable']}", file=sys.stderr)


if __name__ == "__main__":
    main()
