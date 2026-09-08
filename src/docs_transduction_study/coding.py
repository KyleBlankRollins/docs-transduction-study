"""Coding harness for M1a blind coding."""

from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import hmac
import json
import secrets
import sys
from pathlib import Path
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTANCES_CSV = REPO_ROOT / "instruments" / "instances.csv"
PROBES_CSV = REPO_ROOT / "instruments" / "probes.csv"
CODING_DIR = REPO_ROOT / "coding"
MANIFEST_JSON = CODING_DIR / "manifest.json"
MAPPING_ENC = CODING_DIR / "mapping.enc"
M1A_CSV = CODING_DIR / "m1a.csv"

M1A_FIELDS = [
    "opaque_id",
    "artifact_stage",
    "arm",
    "score",
    "score_label",
    "explicit_inferred",
    "option_order",
    "pass_number",
    "session_id",
    "timestamp",
]
ARM_STAGE_COMBOS = [
    ("explicit", "A1"),
    ("explicit", "A2"),
    ("explicit", "A3"),
    ("explicit", "A4"),
    ("implicit", "A1"),
    ("implicit", "A2"),
    ("implicit", "A3"),
    ("implicit", "A4"),
]


def _ensure_coding_dir():
    CODING_DIR.mkdir(parents=True, exist_ok=True)


def _derive_key(seed, purpose, length=32):
    return hmac.new(seed, purpose.encode(), hashlib.sha256).digest()[:length]


def _anonymise(iid, seed):
    key = _derive_key(seed, "anonymise", 16)
    return f"ID-{hashlib.sha256(key + iid.encode()).hexdigest()[:12]}"


def _encrypt_mapping(mapping, key):
    plain = json.dumps(mapping, sort_keys=True).encode()
    stream = hashlib.sha256(key + b"stream").digest()
    while len(stream) < len(plain):
        stream += hashlib.sha256(stream + key).digest()
    return bytes(p ^ s for p, s in zip(plain, stream[: len(plain)]))


def _decrypt_mapping(data, key):
    stream = hashlib.sha256(key + b"stream").digest()
    while len(stream) < len(data):
        stream += hashlib.sha256(stream + key).digest()
    return cast(
        dict[str, str],
        json.loads(bytes(p ^ s for p, s in zip(data, stream[: len(data)])).decode()),
    )


def setup(seed_hex=None):
    _ensure_coding_dir()
    with INSTANCES_CSV.open() as f:
        instances = list(csv.DictReader(f))
    if not instances:
        raise ValueError("empty instances.csv")
    probes = {}
    if PROBES_CSV.exists():
        with PROBES_CSV.open() as f:
            for r in csv.DictReader(f):
                probes[r["instance_id"].strip()] = r
    if not seed_hex:
        seed_hex = secrets.token_hex(32)
    seed = seed_hex.encode()
    entries, mapping, order = [], {}, 0
    for inst in instances:
        iid = inst["instance_id"].strip()
        ikey = _derive_key(seed, f"instance:{iid}", 32)
        for arm, stage in ARM_STAGE_COMBOS:
            oid = _anonymise(f"{iid}-{arm}-{stage}", ikey)
            mapping[oid] = iid
            order += 1
            pr = probes.get(iid, {})
            e = {
                "opaque_id": oid,
                "coding_order": str(order),
                "arm": arm,
                "artifact_stage": stage,
                "artifact_path": inst.get("chunk_explicit", ""),
                "probe_question": pr.get("question", ""),
                "foil_1": pr.get("foil_1", ""),
                "foil_2": pr.get("foil_2", ""),
            }
            entries.append({k: v for k, v in e.items() if v})
    with open(MANIFEST_JSON, "w") as f:
        json.dump(entries, f, indent=2)
    mk = _derive_key(seed, "mapping", 32)
    enc = _encrypt_mapping(mapping, mk)
    sc = hashlib.sha256(seed).hexdigest()[:16]
    with open(MAPPING_ENC, "wb") as f:
        f.write(sc.encode() + enc)
    return {
        "seed": seed_hex,
        "total_instances": len(instances),
        "manifest_entries": len(entries),
        "mapping_encrypted_size": len(enc) + 16,
    }


def _unlock_mapping(seed_hex):
    seed = seed_hex.encode()
    payload = MAPPING_ENC.read_bytes()
    if payload[:16].decode() != hashlib.sha256(seed).hexdigest()[:16]:
        raise ValueError("Seed checksum mismatch")
    return _decrypt_mapping(payload[16:], _derive_key(seed, "mapping", 32))


def decrypt(seed_hex):
    m = _unlock_mapping(seed_hex)
    ts = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
    with open(CODING_DIR / "decrypt_log.txt", "a") as f:
        f.write(f"# decrypted: {ts}\n")
    return m


def code(pass_number=1):
    if not sys.stdin.isatty():
        print("ERROR: code requires TTY", file=sys.stderr)
        sys.exit(1)
    _ensure_coding_dir()
    if not MANIFEST_JSON.exists():
        print("ERROR: run setup first", file=sys.stderr)
        sys.exit(1)
    with open(MANIFEST_JSON) as f:
        manifest = json.load(f)
    total = len(manifest)
    recorded = 0
    session_id = secrets.token_hex(4)
    if not M1A_CSV.exists() or M1A_CSV.stat().st_size == 0:
        with open(M1A_CSV, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=M1A_FIELDS, lineterminator="\n").writeheader()
    for entry in manifest:
        oid = entry["opaque_id"]
        arm = entry.get("arm", "?")
        stg = entry.get("artifact_stage", "?")
        ap = entry.get("artifact_path", "")
        pq = entry.get("probe_question", "")
        f1 = entry.get("foil_1", "")
        f2 = entry.get("foil_2", "")
        order = entry.get("coding_order", "?")
        print(f"\n  [{order}/{total}] {oid} arm={arm} stage={stg}", file=sys.stderr)
        print(f"  Q: {pq}", file=sys.stderr)
        if ap:
            af = REPO_ROOT / ap
            if af.exists():
                for line in af.read_text()[:1500].splitlines():
                    print(f"    {line}", file=sys.stderr)
        opts = ["Preserved: meaning intact"]
        if f1:
            opts.append(f"Corrupted: {f1}")
        else:
            opts.append("Corrupted: wrong relation")
        if f2:
            opts.append(f"Absent: {f2}")
        else:
            opts.append("Absent: text does not say")
        opts.append("Degraded: needs inference")
        import random as _rd

        _rd.Random(hashlib.sha256(f"{session_id}-{oid}".encode()).digest()[:8]).shuffle(
            opts
        )
        sm = {"Preserved": "3", "Degraded": "2", "Absent": "1", "Corrupted": "0"}
        for i, o in enumerate(opts):
            print(f"    [{i + 1}] {o}", file=sys.stderr)
        ch = input("  Score (1-4): ").strip().lower()
        if ch in ("quit", "q", "exit"):
            return {"recorded": recorded, "total": total}
        idx = int(ch) - 1 if ch.isdigit() else -1
        if idx < 0 or idx >= len(opts):
            print("Invalid", file=sys.stderr)
            continue
        chosen = opts[idx]
        score, label = "?", chosen.split(":")[0] if ":" in chosen else chosen
        for k, v in sm.items():
            if chosen.startswith(k):
                score = v
                label = k
                break
        flag = input("  Explicit/Inferred? (e/i): ").strip().lower()
        ei = {"e": "explicit", "i": "inferred"}.get(flag, "unknown")
        ts = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
        row = {
            "opaque_id": oid,
            "artifact_stage": stg,
            "arm": arm,
            "score": score,
            "score_label": label,
            "explicit_inferred": ei,
            "option_order": ";".join(opts),
            "pass_number": str(pass_number),
            "session_id": session_id,
            "timestamp": ts,
        }
        with open(M1A_CSV, "a", newline="") as f:
            csv.DictWriter(f, fieldnames=M1A_FIELDS, lineterminator="\n").writerow(row)
        recorded += 1
    print(f"Complete. {recorded}/{total}", file=sys.stderr)
    return {
        "recorded": recorded,
        "total": total,
        "session_id": session_id,
        "pass": pass_number,
    }


def main():
    p = argparse.ArgumentParser(description="Coding harness")
    sub = p.add_subparsers(dest="mode", required=True)
    sub.add_parser("setup").add_argument("--seed", type=str, default=None)
    sub.add_parser("code").add_argument(
        "--pass", type=int, default=1, dest="pass_number"
    )
    sub.add_parser("decrypt").add_argument("--seed", type=str, required=True)
    args = p.parse_args()
    if args.mode == "setup":
        r = setup(seed_hex=args.seed)
        print(f"Seed: {r['seed']}", file=sys.stderr)
    elif args.mode == "code":
        r = code(pass_number=args.pass_number)
        print(f"Recorded: {r['recorded']}/{r['total']}", file=sys.stderr)
    elif args.mode == "decrypt":
        print(json.dumps(decrypt(args.seed), indent=2))


if __name__ == "__main__":
    main()
