import csv

from docs_transduction_study import m2_redundancy as m2


def write(path, fields, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def setup(tmp_path, judgment_rows):
    instances = tmp_path / "instances.csv"
    write(
        instances,
        ["instance_id", "specimen_id", "relation_type"],
        [
            {"instance_id": "S01-R2-001", "specimen_id": "S01", "relation_type": "R2"},
            {"instance_id": "S01-R3-009", "specimen_id": "S01", "relation_type": "R3"},
        ],
    )
    exclusions = tmp_path / "exclusions.csv"
    write(
        exclusions,
        ["instance_id", "reason"],
        [{"instance_id": "S01-R3-009", "reason": "invalid"}],
    )
    judgments = tmp_path / "judgments.csv"
    write(
        judgments,
        ["instance_id", "cli_static", "runtime", "captures", "evidence_note"],
        judgment_rows,
    )
    captures = tmp_path / "captures"
    captures.mkdir()
    (captures / "add-help.json").write_text("{}")
    out = tmp_path / "m2.csv"
    m2.build_inventory(instances, exclusions, judgments, out)
    return instances, captures, out


def test_defaults_are_unobserved_and_exclusions_marked(tmp_path):
    instances, captures, out = setup(tmp_path, [])
    rows = {row["instance_id"]: row for row in csv.DictReader(out.open())}
    assert (
        rows["S01-R2-001"]["cli_static"]
        == rows["S01-R2-001"]["runtime"]
        == "unobserved"
    )
    assert rows["S01-R3-009"]["docs"] == "not_carried"
    assert m2.validate(out, instances, captures) == []
    table = {row["relation_type"]: row for row in m2.redundancy_map(out)}
    assert table["R2"]["carried_1"] == 1 and table["R3"]["carried_0"] == 1


def test_judgments_must_cite_real_captures(tmp_path):
    rows = [
        {
            "instance_id": "S01-R2-001",
            "cli_static": "carried",
            "runtime": "unobserved",
            "captures": "",
            "evidence_note": "x",
        }
    ]
    instances, captures, out = setup(tmp_path, rows)
    assert any(
        "without a cited capture" in e for e in m2.validate(out, instances, captures)
    )
    rows[0]["captures"] = "missing-capture"
    instances, captures, out = setup(
        tmp_path / "b" if (tmp_path / "b").mkdir() is None else tmp_path, rows
    )
    assert any("unknown captures" in e for e in m2.validate(out, instances, captures))
