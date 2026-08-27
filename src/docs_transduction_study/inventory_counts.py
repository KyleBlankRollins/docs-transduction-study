"""Inventory counts — instances per type and cell-minimum check."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# Minimum cell size per the design (P4 task 6)
CELL_MINIMUM = 20

REQUIRED_TYPES = ["R1", "R2", "R3", "R4", "O1", "O2"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instances", type=Path, default=Path("instruments/instances.csv"))
    parser.add_argument("--specimens", type=Path, default=Path("corpus/specimens.csv"))
    args = parser.parse_args()

    # Read instances
    with args.instances.open("r", encoding="utf-8") as f:
        instances = list(csv.DictReader(f))

    # Count by type
    type_counts: dict[str, int] = {}
    relation_types_seen: set[str] = set()
    specimen_ids_seen: set[str] = set()

    for row in instances:
        rt = row["relation_type"]
        relation_types_seen.add(rt)
        specimen_ids_seen.add(row["specimen_id"])
        type_counts[rt] = type_counts.get(rt, 0) + 1

    # Verify all required types are present
    missing_types = [t for t in REQUIRED_TYPES if t not in relation_types_seen]

    # Build report
    print("=" * 60)
    print("INVENTORY COUNTS REPORT")
    print("=" * 60)
    print(f"Total instances: {len(instances)}")
    print(f"Total specimens: {len(specimen_ids_seen)}")
    print()

    # Per-type breakdown including D3 vs D4 split for R3
    r3_d3 = sum(1 for r in instances if r["relation_type"] == "R3" and r["demark_rule"] == "D3")
    r3_d4 = sum(1 for r in instances if r["relation_type"] == "R3" and r["demark_rule"] == "D4")

    print(f"{'Type':<12} {'Count':>6} {'Cell >=20?':<12}")
    print("-" * 32)
    all_pass = True
    shortfalls: list[str] = []

    for rt in REQUIRED_TYPES:
        count = type_counts.get(rt, 0)
        if rt == "R3":
            detail = f"{count:>6} (D3: {r3_d3}, D4: {r3_d4})"
        else:
            detail = f"{count:>6}"
        ok = "YES" if count >= CELL_MINIMUM else "NO"
        if count < CELL_MINIMUM:
            all_pass = False
            shortfalls.append(f"{rt}={count}")
        print(f"{rt:<12} {detail:>20} {ok:<12}")

    print("-" * 32)
    if missing_types:
        print(f"\nMISSING TYPES: {', '.join(missing_types)}")
        all_pass = False

    print()
    print(f"Demark rules used: {sorted(set(r['demark_rule'] for r in instances if r['demark_rule']))}")

    print()
    if all_pass:
        print("RESULT: ALL CELLS >= 20 — PASS")
    else:
        print(f"RESULT: SHORTFALL on {', '.join(shortfalls)} — needs runlog entry")
        for sf in shortfalls:
            print(f"  {sf}: {type_counts.get(sf.split('=')[0], 0)} (minimum {CELL_MINIMUM})")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()