"""Fail-closed study pipeline: L2 check, A1-A4, anchor resolution, M1-AI packets.

Study artifacts may only be generated after a real, verified L2 commit. The
driver refuses to start otherwise, builds both complete pinned trees with the
ADR-0005 overlay, checks page sets and build determinism, captures default-state
A2 snapshots, extracts A3 strictly, slices A4 losslessly, resolves every retained
instance through the frozen locator spec, and packages exactly eight artifact-only
assignments per retained instance. Any failure stops the run.

``dry-run`` computes the deterministic assignment order, opaque IDs, repeat
sample, and call volume from the instrument and seed alone; it never builds or
reads study artifacts, so it is safe before L2.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from docs_transduction_study import coding_ai, locators

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCK_FILES = (
    "corpus/specimens.csv",
    "instruments/instances.csv",
    "instruments/probes.csv",
    "instruments/gate_exclusions.csv",
    "pipeline/demark/templates.json",
    "coding/seed",
)
# Code whose behavior is part of the frozen instrument (normalization, prompt).
FROZEN_CODE = (
    "src/docs_transduction_study/locators.py",
    "src/docs_transduction_study/coding_ai.py",
)
ARMS = ("explicit", "implicit")
STAGES = ("A1", "A2", "A3", "A4")
CHUNK_SIZE = 1500

Builder = Callable[[str, Path], Path]
Snapshotter = Callable[[Path, str, Path], dict[str, Any]]


class PipelineError(RuntimeError):
    """A condition that must stop study generation."""


def _git(*args: str, repo: Path = REPO_ROOT) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, check=False)


def read_lock_fields(design: str) -> dict[str, str]:
    """Return the L2 frontmatter fields (empty strings when absent or blank)."""
    frontmatter = design.split("\n---", 1)[0] if design.startswith("---") else ""
    fields = {}
    for name in ("instrument_locked", "instrument_lock_commit"):
        match = re.search(
            rf"^{name}:\s*\"?([^\"\n]*)\"?\s*$", frontmatter, re.MULTILINE
        )
        fields[name] = match.group(1).strip() if match else ""
    return fields


def verify_lock(repo: Path = REPO_ROOT) -> dict[str, str]:
    """Verify a real L2 commit whose files are unchanged in the working tree."""
    fields = read_lock_fields((repo / "DESIGN.md").read_text(encoding="utf-8"))
    sha = fields["instrument_lock_commit"]
    if not fields["instrument_locked"] or not re.fullmatch(r"[0-9a-f]{7,40}", sha):
        raise PipelineError(
            "L2 is not recorded in DESIGN.md; study generation is forbidden"
        )
    if _git("cat-file", "-t", sha, repo=repo).stdout.strip() != b"commit":
        raise PipelineError(f"L2 commit {sha} does not exist")
    full = _git("rev-parse", sha, repo=repo).stdout.decode().strip()
    if _git("merge-base", "--is-ancestor", full, "HEAD", repo=repo).returncode != 0:
        raise PipelineError("L2 commit is not an ancestor of HEAD")
    # Unchanged lock files (e.g. specimens, templates) cannot appear in the
    # commit's diff, so presence is checked in the commit's tree; the commit
    # itself may change nothing but lock-set files.
    tree = _git("ls-tree", "-r", "--name-only", full, repo=repo).stdout.decode().split()
    missing = [name for name in LOCK_FILES if name not in tree]
    if missing:
        raise PipelineError(f"L2 commit tree lacks lock-set files: {missing}")
    changed = (
        _git("show", "--name-only", "--format=", full, repo=repo)
        .stdout.decode()
        .split()
    )
    if not changed or not set(changed) <= set(LOCK_FILES):
        raise PipelineError(
            f"L2 commit must change only lock-set files: {sorted(set(changed) - set(LOCK_FILES))}"
        )
    for name in (*LOCK_FILES, *FROZEN_CODE):
        committed = _git("show", f"{full}:{name}", repo=repo)
        if committed.returncode != 0 or committed.stdout != (repo / name).read_bytes():
            raise PipelineError(
                f"{name} differs from the L2 commit; an amendment is required"
            )
    return {"commit": full, "date": fields["instrument_locked"]}


def load_instrument(repo: Path = REPO_ROOT) -> dict[str, Any]:
    def rows(name: str) -> list[dict[str, str]]:
        with (repo / name).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    specimens = {
        row["specimen_id"]: row["source_path"] for row in rows("corpus/specimens.csv")
    }
    excluded = {row["instance_id"] for row in rows("instruments/gate_exclusions.csv")}
    probes = {row["instance_id"]: row for row in rows("instruments/probes.csv")}
    retained = [
        row
        for row in rows("instruments/instances.csv")
        if row["instance_id"] not in excluded
    ]
    if {row["instance_id"] for row in retained} != set(probes):
        raise PipelineError(
            "Retained instances and probes do not correspond one-to-one"
        )
    seed = (repo / "coding" / "seed").read_text(encoding="utf-8").strip()
    if not seed:
        raise PipelineError("The coding-order seed is empty")
    return {
        "specimens": specimens,
        "instances": retained,
        "probes": probes,
        "seed": seed,
    }


def route_for(source_path: str) -> str:
    """Page-relative compiled route of a specimen (never a basename)."""
    return (Path("en") / Path(source_path).with_suffix("") / "index.html").as_posix()


def assignment_id(instance_id: str, arm: str, stage: str) -> str:
    return f"{instance_id}|{arm}|{stage}"


def assignment_plan(instrument: dict[str, Any]) -> dict[str, Any]:
    """Deterministic order, opaque IDs, and repeat sample; needs no artifacts."""
    seed = instrument["seed"]
    identifiers = [
        assignment_id(row["instance_id"], arm, stage)
        for row in instrument["instances"]
        for arm in ARMS
        for stage in STAGES
    ]
    opaque = {
        identifier: coding_ai.opaque_id(identifier, seed) for identifier in identifiers
    }
    if len(set(opaque.values())) != len(opaque):
        raise PipelineError("Opaque identifier collision")
    order = sorted(
        identifiers,
        key=lambda identifier: coding_ai._rank(seed, "order", opaque[identifier]),
    )
    repeat = coding_ai.repeat_sample([opaque[identifier] for identifier in order], seed)
    retained = len(instrument["instances"])
    return {
        "retained_instances": retained,
        "first_pass": len(order),
        "repeats": len(repeat),
        "expected_first_pass": 8 * retained,
        "expected_repeats": math.ceil(0.2 * 8 * retained),
        "order": order,
        "opaque": opaque,
        "repeat_sample": repeat,
        "order_sha256": hashlib.sha256(
            "\n".join(opaque[i] for i in order).encode()
        ).hexdigest(),
    }


def _checksums(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*.html"))
    }


def _default_builder(arm: str, workdir: Path) -> Path:
    from docs_transduction_study.stages import a1_build

    tree = workdir / "tree"
    a1_build._materialise_tree(tree, arm)
    if a1_build._build(tree, arm) != 0:
        raise PipelineError(f"{arm} build failed")
    return tree / "dist"


def build_a1(
    out: Path, routes: dict[str, str], builder: Builder = _default_builder
) -> dict[str, Any]:
    """Two complete builds plus a clean explicit repeat; assets are preserved."""
    checksums: dict[str, dict[str, str]] = {}
    for arm in ARMS:
        with tempfile.TemporaryDirectory(prefix=f"study-a1-{arm}-") as temporary:
            dist = builder(arm, Path(temporary))
            target = out / "a1" / arm
            if target.exists():
                raise PipelineError(
                    f"{target} already exists; artifacts are generated once"
                )
            shutil.copytree(dist, target)
        checksums[arm] = _checksums(out / "a1" / arm)
        if not checksums[arm]:
            raise PipelineError(f"{arm} build produced no HTML")
    if set(checksums["explicit"]) != set(checksums["implicit"]):
        raise PipelineError("Arms produced different page sets")
    for route in routes.values():
        if route not in checksums["explicit"]:
            raise PipelineError(f"Specimen route missing from A1: {route}")
    with tempfile.TemporaryDirectory(prefix="study-a1-repeat-") as temporary:
        repeated = _checksums(builder("explicit", Path(temporary)))
    differing = sorted(
        path
        for path in checksums["explicit"].keys() | repeated.keys()
        if checksums["explicit"].get(path) != repeated.get(path)
    )
    if differing:
        raise PipelineError(f"A1 nondeterminism: {len(differing)} differing HTML pages")
    return {
        "pages": len(checksums["explicit"]),
        "determinism_pages_compared": len(repeated),
        "specimen_html_sha256": {
            arm: {sid: checksums[arm][route] for sid, route in routes.items()}
            for arm in ARMS
        },
    }


def _default_snapshotter(site: Path, route: str, out: Path) -> dict[str, Any]:
    from docs_transduction_study.stages.a2_snapshot import run_snapshot

    return run_snapshot(site, "/" + route.removesuffix("index.html"), out_dir=out)


def capture_a2(
    out: Path, routes: dict[str, str], snapshotter: Snapshotter = _default_snapshotter
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for arm in ARMS:
        for sid, route in routes.items():
            target = out / "a2" / arm / sid
            result = snapshotter(out / "a1" / arm, route, target)
            if not result.get("stable") or not (target / "snapshot-1.txt").is_file():
                raise PipelineError(f"A2 snapshot unstable or missing: {arm}/{sid}")
            results[f"{arm}/{sid}"] = {
                "route": route,
                "stable": True,
                "sha256": hashlib.sha256(
                    (target / "snapshot-1.txt").read_bytes()
                ).hexdigest(),
            }
    return results


def extract_a3(out: Path, routes: dict[str, str]) -> dict[str, Any]:
    from docs_transduction_study.stages.a3_extract import extract_article_text

    results: dict[str, Any] = {}
    for arm in ARMS:
        for sid, route in routes.items():
            text, metadata = extract_article_text(out / "a1" / arm / route)
            target = out / "a3" / arm / Path(route).with_suffix(".txt")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            results[f"{arm}/{sid}"] = {
                **{k: v for k, v in metadata.items() if k != "html_path"},
                "route": route,
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
            }
    return results


def chunk_a4(
    out: Path, routes: dict[str, str], size: int = CHUNK_SIZE
) -> list[dict[str, Any]]:
    index: list[dict[str, Any]] = []
    for arm in ARMS:
        for sid, route in routes.items():
            text = (out / "a3" / arm / Path(route).with_suffix(".txt")).read_text(
                encoding="utf-8"
            )
            pieces = [text[i : i + size] for i in range(0, len(text), size)]
            if "".join(pieces) != text or not pieces:
                raise PipelineError(f"A4 slicing is not lossless for {arm}/{sid}")
            for number, piece in enumerate(pieces):
                path = (
                    Path("a4")
                    / arm
                    / Path(route).with_suffix("")
                    / f"chunk-{number:04d}.txt"
                )
                (out / path).parent.mkdir(parents=True, exist_ok=True)
                (out / path).write_text(piece, encoding="utf-8")
                index.append(
                    {
                        "arm": arm,
                        "specimen_id": sid,
                        "route": route,
                        "chunk_index": number,
                        "chunk_start": number * size,
                        "char_count": len(piece),
                        "chunk_path": path.as_posix(),
                        "sha256": hashlib.sha256(piece.encode()).hexdigest(),
                    }
                )
    return index


def _visible_text(html: str) -> str:
    from bs4 import BeautifulSoup

    return BeautifulSoup(html, "html.parser").get_text(separator=" ")


def resolve_instances(
    out: Path, instrument: dict[str, Any], chunks: list[dict[str, Any]], corpus: Path
) -> list[dict[str, Any]]:
    """Locate every retained instance per arm; A3/A4 failures stop the run."""
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for row in instrument["instances"]:
        sid = row["specimen_id"]
        route = route_for(instrument["specimens"][sid])
        record: dict[str, Any] = {
            "instance_id": row["instance_id"],
            "specimen_id": sid,
            "route": route,
        }
        for arm in ARMS:
            source = (corpus / arm / instrument["specimens"][sid]).read_text(
                encoding="utf-8"
            )
            text = (out / "a3" / arm / Path(route).with_suffix(".txt")).read_text(
                encoding="utf-8"
            )
            try:
                span = locators.resolve_host(row[f"host_passage_{arm}"], source, text)
                locators.resolve_anchor(row[f"anchor_{arm}"], text, span)
            except ValueError as error:
                failures.append(f"{row['instance_id']}/{arm}: {error}")
                continue
            page_chunks = [c for c in chunks if c["arm"] == arm and c["route"] == route]
            start = next(
                c
                for c in page_chunks
                if c["chunk_start"] <= span[0] < c["chunk_start"] + c["char_count"]
            )
            end = next(
                c
                for c in page_chunks
                if c["chunk_start"] <= span[1] - 1 < c["chunk_start"] + c["char_count"]
            )
            html = (out / "a1" / arm / route).read_text(encoding="utf-8")
            snapshot = (out / "a2" / arm / sid / "snapshot-1.txt").read_text(
                encoding="utf-8"
            )
            record[arm] = {
                "host_span": list(span),
                "chunk_path": start["chunk_path"],
                "chunk_index": start["chunk_index"],
                "spans_chunks": start["chunk_index"] != end["chunk_index"],
                "anchor_in_a1": bool(
                    locators.find_all(row[f"anchor_{arm}"], _visible_text(html))
                ),
                # Absence at A2 may be structural (default-hidden content), not a defect.
                "anchor_in_a2": bool(locators.find_all(row[f"anchor_{arm}"], snapshot)),
            }
            if not record[arm]["anchor_in_a1"]:
                failures.append(
                    f"{row['instance_id']}/{arm}: anchor absent from compiled HTML"
                )
        rows.append(record)
    if failures:
        raise PipelineError(
            "Anchor resolution failed (mechanical amendment required): "
            + "; ".join(failures)
        )
    return rows


def _seal(plaintext: bytes, passphrase_file: Path) -> bytes:
    result = subprocess.run(
        [
            "openssl",
            "enc",
            "-aes-256-cbc",
            "-pbkdf2",
            "-iter",
            "600000",
            "-salt",
            "-pass",
            f"file:{passphrase_file}",
        ],
        input=plaintext,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise PipelineError("Sealing the scoring keys failed")
    return result.stdout


def unseal(path: Path, passphrase_file: Path) -> bytes:
    result = subprocess.run(
        [
            "openssl",
            "enc",
            "-d",
            "-aes-256-cbc",
            "-pbkdf2",
            "-iter",
            "600000",
            "-pass",
            f"file:{passphrase_file}",
            "-in",
            str(path),
        ],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise PipelineError("Unsealing the scoring keys failed")
    return result.stdout


def package_assignments(
    out: Path,
    instrument: dict[str, Any],
    resolved: list[dict[str, Any]],
    *,
    passphrase_file: Path | None,
    max_packet_bytes: int = 1_500_000,
) -> dict[str, Any]:
    """Write ordered public packets and separately sealed scoring keys."""
    plan = assignment_plan(instrument)
    by_instance = {record["instance_id"]: record for record in resolved}
    packets: dict[str, dict[str, Any]] = {}
    keys: list[dict[str, Any]] = []
    for identifier in plan["order"]:
        instance_id, arm, stage = identifier.split("|")
        record = by_instance[instance_id]
        route = record["route"]
        if stage == "A1":
            artifact = (out / "a1" / arm / route).read_text(encoding="utf-8")
        elif stage == "A2":
            artifact = (
                out / "a2" / arm / record["specimen_id"] / "snapshot-1.txt"
            ).read_text(encoding="utf-8")
        elif stage == "A3":
            artifact = (out / "a3" / arm / Path(route).with_suffix(".txt")).read_text(
                encoding="utf-8"
            )
        else:
            # Exactly the chunk containing this arm's host-passage start.
            artifact = (out / record[arm]["chunk_path"]).read_text(encoding="utf-8")
        packet, key = coding_ai.prepare_packet(
            identifier, artifact, instrument["probes"][instance_id], instrument["seed"]
        )
        size = len(json.dumps(packet, ensure_ascii=False).encode())
        if size > max_packet_bytes:
            raise PipelineError(
                f"{identifier} packet is {size} bytes; artifacts are never truncated"
            )
        packets[packet["opaque_id"]] = packet
        keys.append(
            {
                **key,
                "arm": arm,
                "stage": stage,
                "spans_chunks": record[arm]["spans_chunks"] if stage == "A4" else None,
            }
        )
    if len(packets) != plan["expected_first_pass"]:
        raise PipelineError("Assignment count is not eight per retained instance")
    public = out / "assignments"
    public.mkdir(parents=True, exist_ok=False)
    ordered = [packets[plan["opaque"][identifier]] for identifier in plan["order"]]
    (public / "packets.jsonl").write_text(
        "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in ordered),
        encoding="utf-8",
    )
    repeat = set(plan["repeat_sample"])
    (public / "repeat_packets.jsonl").write_text(
        "".join(
            json.dumps(p, ensure_ascii=False) + "\n"
            for p in ordered
            if p["opaque_id"] in repeat
        ),
        encoding="utf-8",
    )
    plaintext = "".join(json.dumps(k) + "\n" for k in keys).encode()
    private = out / "private"
    private.mkdir(mode=0o700, exist_ok=False)
    if passphrase_file is None:
        raise PipelineError(
            "A passphrase file outside the repository is required to seal scoring keys"
        )
    if passphrase_file.resolve().is_relative_to(REPO_ROOT):
        raise PipelineError("The passphrase file must be outside the repository")
    (private / "keys.jsonl.enc").write_bytes(_seal(plaintext, passphrase_file))
    os.chmod(private / "keys.jsonl.enc", 0o600)
    manifest = {
        "first_pass": len(ordered),
        "repeats": len(repeat),
        "order_sha256": plan["order_sha256"],
        "packets_sha256": hashlib.sha256(
            (public / "packets.jsonl").read_bytes()
        ).hexdigest(),
        "keys_plaintext_sha256": hashlib.sha256(plaintext).hexdigest(),
        "max_packet_bytes": max(
            len(json.dumps(p, ensure_ascii=False).encode()) for p in ordered
        ),
        "per_stage": {
            stage: sum(1 for i in plan["order"] if i.endswith(stage))
            for stage in STAGES
        },
    }
    (public / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return manifest


def run_study(
    out: Path,
    *,
    passphrase_file: Path | None,
    repo: Path = REPO_ROOT,
    builder: Builder | None = None,
    snapshotter: Snapshotter | None = None,
    lock_verifier: Callable[[Path], dict[str, str]] = verify_lock,
) -> dict[str, Any]:
    lock = lock_verifier(repo)
    if passphrase_file is not None:
        # Make passes quoted paths, so the shell never expands "~".
        passphrase_file = passphrase_file.expanduser()
    if passphrase_file is None or any(
        passphrase_file.resolve().is_relative_to(root.resolve())
        for root in (REPO_ROOT, repo)
    ):
        raise PipelineError(
            "A passphrase file outside the repository is required before generation"
        )
    if not passphrase_file.is_file() or not passphrase_file.read_text().strip():
        raise PipelineError(f"Passphrase file is missing or empty: {passphrase_file}")
    # Resolved at call time so tests can forbid the real build and browser.
    builder = builder or _default_builder
    snapshotter = snapshotter or _default_snapshotter
    instrument = load_instrument(repo)
    routes = {sid: route_for(path) for sid, path in instrument["specimens"].items()}
    out.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {"lock": lock, "chunk_size": CHUNK_SIZE}
    manifest["a1"] = build_a1(out, routes, builder)
    manifest["a2"] = capture_a2(out, routes, snapshotter)
    manifest["a3"] = extract_a3(out, routes)
    chunks = chunk_a4(out, routes)
    (out / "a4-index.json").write_text(json.dumps(chunks, indent=2), encoding="utf-8")
    resolved = resolve_instances(out, instrument, chunks, repo / "corpus")
    (out / "anchor-assignments.json").write_text(
        json.dumps(resolved, indent=2), encoding="utf-8"
    )
    manifest["assignments"] = package_assignments(
        out, instrument, resolved, passphrase_file=passphrase_file
    )
    (out / "study-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return manifest


def dry_run(repo: Path = REPO_ROOT) -> dict[str, Any]:
    """Assignment plan and call volume without any study artifact."""
    plan = assignment_plan(load_instrument(repo))
    summary = {
        key: plan[key]
        for key in (
            "retained_instances",
            "first_pass",
            "repeats",
            "expected_first_pass",
            "expected_repeats",
            "order_sha256",
        )
    }
    summary["per_stage_arm"] = {
        f"{arm}/{stage}": plan["retained_instances"] for arm in ARMS for stage in STAGES
    }
    summary["minimum_invocations"] = plan["first_pass"] + plan["repeats"]
    return {
        "summary": summary,
        "order": [plan["opaque"][i] for i in plan["order"]],
        "repeat_sample": plan["repeat_sample"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    dry = sub.add_parser("dry-run", help="assignment plan only; no artifacts")
    dry.add_argument(
        "--out", type=Path, default=REPO_ROOT / "build" / "assignment-dry-run.json"
    )
    run = sub.add_parser("run", help="generate study artifacts (requires verified L2)")
    run.add_argument("--out", type=Path, default=REPO_ROOT / "artifacts")
    run.add_argument("--passphrase-file", type=Path, required=True)
    sub.add_parser("verify-lock", help="check the recorded L2 commit and lock set")
    args = parser.parse_args()
    try:
        if args.command == "verify-lock":
            print(json.dumps(verify_lock(), indent=2))
        elif args.command == "dry-run":
            result = dry_run()
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result["summary"], indent=2))
        else:
            print(
                json.dumps(
                    run_study(args.out, passphrase_file=args.passphrase_file), indent=2
                )
            )
    except PipelineError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
