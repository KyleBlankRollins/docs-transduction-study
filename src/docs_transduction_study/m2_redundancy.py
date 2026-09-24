"""M2 redundancy inventory (AI-assisted, amendment A3): observed channel evidence.

``capture`` runs bounded commands against the pinned Astro CLI in a disposable
sandbox outside the repository (the pinned ``node_modules`` is borrowed
read-only; Vite and Astro caches are redirected into the sandbox) and stores raw
observations under ``coding/m2_captures/``. ``inventory`` writes
``coding/m2_redundancy.csv``: one row per instance with the documentation,
CLI-static, and runtime channels marked ``carried``, ``not_carried``, or
``unobserved``. ``not_carried`` requires a captured surface that addresses the
relation's subject; anything not examined is ``unobserved`` — never a confirmed
absence.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PINNED_MODULES = REPO_ROOT / "vendor" / "astro-docs" / "node_modules"
CAPTURES = REPO_ROOT / "coding" / "m2_captures"
INVENTORY = REPO_ROOT / "coding" / "m2_redundancy.csv"
CHANNELS = ("docs", "cli_static", "runtime")
VALUES = {"carried", "not_carried", "unobserved"}

CONFIG = """import {{ defineConfig }} from 'astro/config';
export default defineConfig({{
  {output}
  cacheDir: './.astro-cache',
  vite: {{ cacheDir: './.vite-cache' }},
}});
"""
COMMANDS: dict[str, tuple[list[str], str]] = {
    "version": (["--version"], "static"),
    "help": (["--help"], "static"),
    "add-help": (["add", "--help"], "static"),
    "dev-help": (["dev", "--help"], "static"),
    "build-help": (["build", "--help"], "static"),
    "preview-help": (["preview", "--help"], "static"),
    "build-static": (["build"], "static-project"),
    "build-server-no-adapter": (["build"], "server-project"),
}


def _sanitize(text: str, root: Path) -> str:
    return text.replace(str(root), "<sandbox>").replace(str(REPO_ROOT), "<repo>")


def _sandbox(root: Path, output: str) -> None:
    (root / "src" / "pages").mkdir(parents=True)
    (root / "package.json").write_text(
        json.dumps({"name": "m2-sandbox", "type": "module", "private": True})
    )
    (root / "astro.config.mjs").write_text(CONFIG.format(output=output))
    (root / "src" / "pages" / "index.astro").write_text("<h1>M2 sandbox</h1>\n")
    (root / "node_modules").symlink_to(PINNED_MODULES, target_is_directory=True)


def capture(out: Path = CAPTURES, timeout: float = 120.0) -> list[dict[str, Any]]:
    """Run bounded CLI/runtime observations and store them verbatim."""
    if not (PINNED_MODULES / ".bin" / "astro").exists():
        raise FileNotFoundError("Pinned Astro CLI is not installed in the vendor tree")
    out.mkdir(parents=True, exist_ok=True)
    node = subprocess.run(
        ["node", "--version"], capture_output=True, text=True, check=False
    )
    results = []
    for name, (args, kind) in COMMANDS.items():
        root = Path(tempfile.mkdtemp(prefix="m2-sandbox-")).resolve()
        try:
            output = "output: 'server'," if kind == "server-project" else ""
            _sandbox(root, output)
            env = {**os.environ, "ASTRO_TELEMETRY_DISABLED": "1", "CI": "1"}
            try:
                result = subprocess.run(
                    [
                        "node",
                        str(PINNED_MODULES / "astro" / "bin" / "astro.mjs"),
                        *args,
                    ],
                    cwd=root,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                exit_code, stdout, stderr = (
                    result.returncode,
                    result.stdout,
                    result.stderr,
                )
            except subprocess.TimeoutExpired:
                exit_code, stdout, stderr = None, "", f"timeout after {timeout}s"
            record = {
                "capture_id": name,
                "command": "astro " + " ".join(args),
                "project": kind,
                "exit_code": exit_code,
                "stdout": _sanitize(stdout, root),
                "stderr": _sanitize(stderr, root),
                "node_version": node.stdout.strip(),
                "captured_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "label": "AI-assisted observation (amendment A3)",
            }
            (out / f"{name}.json").write_text(
                json.dumps(record, indent=2), encoding="utf-8"
            )
            results.append(record)
        finally:
            (root / "node_modules").unlink(missing_ok=True)
            shutil.rmtree(root, ignore_errors=True)
    return results


INVENTORY_FIELDS = [
    "instance_id",
    "specimen_id",
    "relation_type",
    *CHANNELS,
    "captures",
    "evidence_note",
    "label",
]
DEFAULT_NOTE = (
    "Documentation carries the relation in both A0 arms (host passage). No captured "
    "Astro CLI or runtime surface addresses this relation's subject; not observed, "
    "not a confirmed absence."
)


def build_inventory(
    instances: Path, exclusions: Path, judgments: Path, out: Path = INVENTORY
) -> int:
    """Combine explicit capture-backed judgments with conservative defaults."""
    with exclusions.open(encoding="utf-8", newline="") as handle:
        excluded = {row["instance_id"]: row["reason"] for row in csv.DictReader(handle)}
    explicit = load_judgments(judgments)
    rows = []
    with instances.open(encoding="utf-8", newline="") as handle:
        for instance in csv.DictReader(handle):
            identifier = instance["instance_id"]
            row = {
                "instance_id": identifier,
                "specimen_id": instance["specimen_id"],
                "relation_type": instance["relation_type"],
                "docs": "carried",
                "cli_static": "unobserved",
                "runtime": "unobserved",
                "captures": "",
                "evidence_note": DEFAULT_NOTE,
                "label": "AI-assisted (amendment A3)",
            }
            if identifier in excluded:
                row["docs"] = "not_carried"
                row["evidence_note"] = f"Excluded at the gate: {excluded[identifier]}"
            if identifier in explicit:
                judged = explicit[identifier]
                row.update(
                    {
                        k: judged[k]
                        for k in ("cli_static", "runtime", "captures", "evidence_note")
                    }
                )
            rows.append(row)
    unknown = set(explicit) - {row["instance_id"] for row in rows}
    if unknown:
        raise ValueError(f"Judgments for unknown instances: {sorted(unknown)}")
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=INVENTORY_FIELDS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def load_judgments(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["instance_id"]: row for row in csv.DictReader(handle)}


def validate(inventory: Path, instances: Path, captures: Path) -> list[str]:
    """Every instance has one row; values are known; evidence cites real captures."""
    with instances.open(encoding="utf-8", newline="") as handle:
        expected = {row["instance_id"] for row in csv.DictReader(handle)}
    rows = load_judgments(inventory)
    errors = []
    if set(rows) != expected:
        errors.append(
            f"coverage mismatch: missing {sorted(expected - set(rows))[:5]}, foreign {sorted(set(rows) - expected)[:5]}"
        )
    available = {path.stem for path in captures.glob("*.json")}
    for identifier, row in rows.items():
        for channel in CHANNELS:
            if row[channel] not in VALUES:
                errors.append(
                    f"{identifier}: {channel} has invalid value {row[channel]!r}"
                )
        if not row["evidence_note"].strip():
            errors.append(f"{identifier}: empty evidence_note")
        cited = {c for c in row["captures"].split(";") if c}
        if cited - available:
            errors.append(
                f"{identifier}: cites unknown captures {sorted(cited - available)}"
            )
        if (
            row["cli_static"] != "unobserved" or row["runtime"] != "unobserved"
        ) and not cited:
            errors.append(f"{identifier}: CLI/runtime judgment without a cited capture")
    return errors


def redundancy_map(inventory: Path) -> list[dict[str, Any]]:
    """Channels carrying each relation, counted per relation type."""
    rows = load_judgments(inventory).values()
    table: dict[str, dict[str, int]] = {}
    for row in rows:
        counts = table.setdefault(
            row["relation_type"],
            {"instances": 0, "unobserved_any": 0}
            | {f"carried_{n}": 0 for n in range(4)},
        )
        counts["instances"] += 1
        carried = sum(row[channel] == "carried" for channel in CHANNELS)
        counts[f"carried_{carried}"] += 1
        counts["unobserved_any"] += any(
            row[channel] == "unobserved" for channel in CHANNELS
        )
    return [{"relation_type": key, **value} for key, value in sorted(table.items())]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("capture")
    sub.add_parser("inventory")
    sub.add_parser("validate")
    sub.add_parser("map")
    args = parser.parse_args()
    if args.command == "capture":
        for record in capture():
            print(f"{record['capture_id']}: exit {record['exit_code']}")
    elif args.command == "inventory":
        count = build_inventory(
            REPO_ROOT / "instruments" / "instances.csv",
            REPO_ROOT / "instruments" / "gate_exclusions.csv",
            REPO_ROOT / "coding" / "m2_judgments.csv",
        )
        print(f"wrote {count} rows to {INVENTORY}")
    elif args.command == "validate":
        errors = validate(
            INVENTORY, REPO_ROOT / "instruments" / "instances.csv", CAPTURES
        )
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1 if errors else 0)
    else:
        print(json.dumps(redundancy_map(INVENTORY), indent=2))


if __name__ == "__main__":
    main()
