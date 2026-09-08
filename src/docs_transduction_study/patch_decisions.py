"""Patch review CSVs with human classification decisions from provided data."""

import csv
from pathlib import Path

# The 49 rejected O1 entries (instance_id -> rejection_reason)
O1_REJECTED = {
    "S01-O1-010": "generic",
    "S01-O1-015": "duplicate_boundary",
    "S01-O1-018": "idiom",
    "S01-O1-020": "generic",
    "S01-O1-023": "idiom",
    "S01-O1-033": "duplicate_boundary",
    "S01-O1-040": "not_probeable",
    "S01-O1-043": "generic",
    "S01-O1-049": "generic",
    "S02-O1-010": "generic",
    "S02-O1-012": "duplicate_boundary",
    "S02-O1-039": "not_probeable",
    "S03-O1-001": "not_probeable",
    "S03-O1-005": "not_probeable",
    "S03-O1-006": "not_probeable",
    "S03-O1-013": "not_probeable",
    "S03-O1-014": "not_probeable",
    "S03-O1-021": "generic",
    "S04-O1-004": "generic",
    "S04-O1-018": "not_probeable",
    "S04-O1-023": "generic",
    "S04-O1-033": "not_probeable",
    "S04-O1-034": "generic",
    "S05-O1-009": "not_probeable",
    "S05-O1-012": "not_probeable",
    "S05-O1-013": "not_probeable",
    "S05-O1-016": "generic",
    "S05-O1-020": "generic",
    "S06-O1-007": "generic",
    "S06-O1-009": "not_probeable",
    "S06-O1-016": "duplicate_boundary",
    "S07-O1-007": "not_probeable",
    "S07-O1-009": "duplicate_boundary",
    "S07-O1-013": "not_probeable",
    "S07-O1-017": "not_probeable",
    "S07-O1-018": "not_probeable",
    "S08-O1-006": "generic",
    "S08-O1-007": "generic",
    "S09-O1-026": "generic",
    "S09-O1-032": "generic",
    "S10-O1-001": "generic",
    "S10-O1-023": "not_probeable",
    "S11-O1-010": "generic",
    "S11-O1-017": "generic",
    "S11-O1-032": "idiom",
    "S11-O1-035": "not_probeable",
    "S11-O1-048": "not_probeable",
    "S11-O1-049": "not_probeable",
    "S12-O1-017": "idiom",
}

# The 4 rejected O2 entries
O2_REJECTED = {
    "S02-O2-004": "duplicate_boundary",
    "S02-O2-006": "duplicate_boundary",
    "S05-O2-004": "duplicate_boundary",
    "S10-O2-008": "duplicate_boundary",
}


def patch_csv(path: Path, rejected: dict[str, str]) -> None:
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    fieldnames = list(rows[0].keys())
    accepted = 0
    rejected_count = 0

    for row in rows:
        iid = row["instance_id"]
        if iid in rejected:
            row["accept"] = "NO"
            row["rejection_reason"] = rejected[iid]
            rejected_count += 1
        else:
            row["accept"] = "YES"
            accepted += 1

    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    print(f"{path.name}: {accepted} YES, {rejected_count} NO")


patch_csv(Path("instruments/o1_review.csv"), O1_REJECTED)
patch_csv(Path("instruments/o2_review.csv"), O2_REJECTED)
print("Done.")
