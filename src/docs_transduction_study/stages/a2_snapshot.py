"""A2 — Playwright accessibility snapshot of the served page.

Default page state, no interaction. Snapshots the pilot page twice and diffs
to verify tree stability across loads.

Usage:
    uv run python -m docs_transduction_study.stages.a2_snapshot --tree-dir DIR
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"


def _get_snapshot(port: int, path: str) -> str:
    """Use Playwright to get the accessibility tree of a page."""
    from playwright.sync_api import sync_playwright

    url = f"http://localhost:{port}{path}"
    print(f"  fetching: {url}", file=sys.stderr)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        response = page.goto(url, wait_until="networkidle")
        if response is None or not response.ok:
            browser.close()
            raise ValueError(f"A2 could not load the compiled page: {url}")
        page.wait_for_timeout(1000)
        snapshot = page.locator("body").aria_snapshot()
        browser.close()
    return snapshot


def _diff_snapshots(a: dict | str, b: dict | str, path: str = "") -> list[str]:
    """Recursively diff two accessibility snapshots."""
    if isinstance(a, str) or isinstance(b, str):
        return [] if a == b else ["Accessibility snapshots differ"]
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


def _start_artifact_server(
    tree_dir: Path, port: int
) -> tuple[ThreadingHTTPServer, Thread]:
    """Serve existing compiled output only, on the loopback interface."""
    if not tree_dir.is_dir():
        raise FileNotFoundError(f"Compiled artifact directory not found: {tree_dir}")
    handler = partial(SimpleHTTPRequestHandler, directory=str(tree_dir.resolve()))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def run_snapshot(
    tree_dir: Path, page_path: str, port: int = 0, out_dir: Path | None = None
) -> dict[str, Any]:
    """Snapshot the served page's accessibility tree twice. Returns results."""
    if out_dir is None:
        out_dir = ARTIFACTS_DIR / "a2"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Serving compiled artifacts from {tree_dir}...", file=sys.stderr)
    server, thread = _start_artifact_server(tree_dir, port)
    port = server.server_port

    try:
        snap1 = _get_snapshot(port, page_path)
        if not snap1:
            return {"error": "snapshot returned empty output"}
        snap2 = _get_snapshot(port, page_path)
        if not snap2:
            return {"error": "snapshot 2 returned empty output"}

        (out_dir / "snapshot-1.json").write_text(
            json.dumps(snap1, indent=2), encoding="utf-8"
        )
        (out_dir / "snapshot-2.json").write_text(
            json.dumps(snap2, indent=2), encoding="utf-8"
        )

        (out_dir / "snapshot-1.txt").write_text(snap1, encoding="utf-8")
        (out_dir / "snapshot-2.txt").write_text(snap2, encoding="utf-8")

        diffs = _diff_snapshots(snap1, snap2)
        tab_details = [
            line
            for line in snap1.splitlines()
            if re.match(r"\s*- (?:tablist|tab|tabpanel)\b", line)
        ]

        return {
            "page_path": page_path,
            "snapshot_count": 2,
            "diffs": diffs,
            "stable": len(diffs) == 0,
            "tab_roles_found": len(tab_details) > 0,
            "tab_details": tab_details,
            "snapshot_format": "Playwright Locator.aria_snapshot YAML",
            "snapshot_lines_1": len(snap1.splitlines()),
            "snapshot_lines_2": len(snap2.splitlines()),
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)
        print("Artifact server stopped.", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tree-dir", type=Path, required=True, help="Compiled A1 root with assets"
    )
    parser.add_argument("--page", type=str, default="/en/install-and-setup/")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--out", type=Path, default=ARTIFACTS_DIR / "a2")
    args = parser.parse_args()
    results = run_snapshot(args.tree_dir, args.page, args.port, args.out)
    if "error" in results:
        print(f"ERROR: {results['error']}", file=sys.stderr)
        sys.exit(1)
    print(f"\nStable: {results['stable']}", file=sys.stderr)


if __name__ == "__main__":
    main()
