import csv
import textwrap

import pytest

from docs_transduction_study import instrument_authoring as authoring

EXPLICIT = """---
title: Page
---
Install the package first. Then open the settings file.

:::tip
You can customize the settings to your needs.
:::

Save the settings file after editing it.
"""
IMPLICIT = """---
title: Page
---
Install the package first. Then open the settings file.

As a helpful tip, You can customize the settings to your needs.

Save the settings file after editing it.
"""


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def workspace(tmp_path):
    corpus = tmp_path / "corpus"
    for arm, text in (("explicit", EXPLICIT), ("implicit", IMPLICIT)):
        (corpus / arm).mkdir(parents=True)
        (corpus / arm / "page.mdx").write_text(text, encoding="utf-8")
    write_csv(
        corpus / "specimens.csv",
        ["specimen_id", "source_path"],
        [{"specimen_id": "S01", "source_path": "page.mdx"}],
    )
    first = EXPLICIT.index("the settings file")
    second = EXPLICIT.index("the settings file", first + 1)
    review = []
    for offset in (first, second):
        implicit_offset = IMPLICIT.index(
            "the settings file", 0 if offset == first else IMPLICIT.index("Save")
        )
        review.append(
            {
                "instance_id": f"S01-O1-at-{offset:06d}",
                "specimen_id": "S01",
                "relation_type": "O1",
                "expression": "the settings file",
                "explicit_start": offset,
                "explicit_end": offset + 17,
                "implicit_start": implicit_offset,
                "implicit_end": implicit_offset + 17,
            }
        )
    write_csv(tmp_path / "review" / "o1_review.csv", list(review[0]), review)
    write_csv(tmp_path / "review" / "o2_review.csv", list(review[0]), [])
    instruments = tmp_path / "instruments"
    legacy_fields = [
        "instance_id",
        "specimen_id",
        "relation_type",
        "expression",
        "accept",
        "rejection_reason",
    ]
    write_csv(
        instruments / "o1_review.csv",
        legacy_fields,
        [
            {
                "instance_id": "S01-O1-001",
                "specimen_id": "S01",
                "relation_type": "O1",
                "expression": "the settings file",
                "accept": "YES",
                "rejection_reason": "",
            }
        ],
    )
    write_csv(instruments / "o2_review.csv", legacy_fields, [])
    write_csv(
        instruments / "instances.csv",
        authoring.INSTANCE_FIELDS,
        [
            {
                "instance_id": "S01-R3-001",
                "specimen_id": "S01",
                "relation_type": "R3",
                "anchor_explicit": "",
                "anchor_implicit": "",
                "host_passage_explicit": "",
                "host_passage_implicit": "",
                "demark_rule": "D3",
                "notes": ":::tip directive",
            }
        ],
    )
    return tmp_path, [row["instance_id"] for row in review]


RELATION = '''
[[relation]]
id = "S01-R3-001"
reason = "tip aside"
host = """:::tip
You can customize the settings to your needs."""
host_implicit = "As a helpful tip, You can customize the settings to your needs."
anchor = "customize the settings to your needs"
question = "How does the page present adjusting the configuration?"
correct = "As an optional adjustment"
foil_1 = "As a mandatory step"
evidence = "You can customize"
gate = "pass"
'''


def accepted(identifier, **overrides):
    fields = {
        "id": identifier,
        "decision": "accept",
        "reason": "anaphor to the file opened earlier",
        "host_from": "Install the package first.",
        "host_to": "Save the settings file after editing it.",
        "anchor": "Save the settings file after",
        "question": "Which file is saved after editing?",
        "correct": "The configuration file opened earlier",
        "foil_1": "The installed package",
        "evidence": "Then open the settings file.",
        "gate": "pass",
    }
    fields.update(overrides)
    body = "\n".join(
        f"{key} = {value!r}".replace("'", '"') for key, value in fields.items()
    )
    return "\n[[candidate]]\n" + body + "\n"


def run(workspace_path, text, write=False):
    authoring_dir = workspace_path / "authoring"
    authoring_dir.mkdir(exist_ok=True)
    (authoring_dir / "S01.toml").write_text(textwrap.dedent(text), encoding="utf-8")
    return authoring.build(
        authoring_dir=authoring_dir,
        instruments=workspace_path / "instruments",
        review_dir=workspace_path / "review",
        corpus=workspace_path / "corpus",
        date="2026-09-23",
        write=write,
    )


def rejected(identifier, reason="generic: reader-possessive"):
    return f'\n[[candidate]]\nid = "{identifier}"\ndecision = "reject"\nreason = "{reason}"\n'


def test_complete_review_writes_traceable_instrument(workspace):
    path, (first, second) = workspace
    summary = run(path, rejected(first) + accepted(second) + RELATION, write=True)
    assert summary["errors"] == []
    instruments = path / "instruments"
    instances = list(csv.DictReader((instruments / "instances.csv").open()))
    assert [row["instance_id"] for row in instances] == ["S01-R3-001", second]
    occurrence = instances[1]
    assert "legacy S01-O1-001 (YES, occurrence 2)" in occurrence["notes"]
    assert occurrence["host_passage_explicit"].startswith("Install the package first.")
    decisions = list(csv.DictReader((instruments / "occurrence_decisions.csv").open()))
    assert {row["decision"] for row in decisions} == {"accept", "reject"}
    assert [row["occurrence_rank"] for row in decisions] == ["1", "2"]
    probes = list(csv.DictReader((instruments / "probes.csv").open()))
    assert len(probes) == 2 and probes[0]["version_change"] == "false"
    evidence = list(csv.DictReader((instruments / "gate_evidence.csv").open()))
    assert len(evidence) == 4 and all(row["evidence"] for row in evidence)


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        (lambda second: "", "unreviewed"),
        (lambda second: rejected(second, "because"), "rejection reason needs a code"),
        (
            lambda second: accepted(second, host_to="Then open the settings file."),
            "does not contain the reviewed occurrence",
        ),
        (
            lambda second: accepted(second, anchor="the settings file"),
            "anchor is not unique",
        ),
        (
            lambda second: accepted(second, evidence="Invented quote"),
            "not a verbatim quote",
        ),
        (
            lambda second: accepted(second, correct="Install the package first."),
            "VERBATIM",
        ),
        (lambda second: accepted(second, host_from="the settings"), "exactly once"),
    ],
)
def test_review_errors_fail_closed_without_writing(workspace, entry, message):
    path, (first, second) = workspace
    before = (path / "instruments" / "instances.csv").read_bytes()
    summary = run(path, rejected(first) + entry(second) + RELATION, write=True)
    assert any(message in error for error in summary["errors"]), summary["errors"]
    assert (path / "instruments" / "instances.csv").read_bytes() == before
    assert not (path / "instruments" / "probes.csv").exists()


def test_gate_failures_and_invalid_instances_become_dated_exclusions(workspace):
    path, (first, second) = workspace
    failing = accepted(
        second,
        gate="fail",
        failed_arm="implicit",
        reason_gate="implicit arm does not say",
    )
    invalid = """
[[relation]]
id = "S01-R3-001"
reason = "not an admonition"
invalid = true
gate = "fail"
failed_arm = "both"
reason_gate = "matched HTML inside a code example"
"""
    summary = run(path, rejected(first) + failing + invalid, write=True)
    assert summary["errors"] == [] and summary["probes"] == 0
    exclusions = list(
        csv.DictReader((path / "instruments" / "gate_exclusions.csv").open())
    )
    assert {row["failed_arm"] for row in exclusions} == {"implicit", "both"}
    assert all(row["date"] == "2026-09-23" and row["reason"] for row in exclusions)


def test_host_after_disambiguates_repeated_text(workspace):
    path, (first, second) = workspace
    options = {
        "host_from": "the settings file",
        "host_to": "after editing it.",
        "anchor": "settings file after editing",
        "evidence": "after editing it",
    }
    ambiguous = run(path, rejected(first) + accepted(second, **options) + RELATION)
    assert any("exactly once" in error for error in ambiguous["errors"])
    marked = accepted(second, host_after="customize", **options)
    summary = run(path, rejected(first) + marked + RELATION, write=True)
    assert summary["errors"] == []
    rows = list(csv.DictReader((path / "instruments" / "instances.csv").open()))
    assert rows[1]["host_passage_explicit"] == "the settings file after editing it."


def test_hosts_may_not_start_inside_code(workspace):
    path, (first, second) = workspace
    source = EXPLICIT.replace(
        "Install the package first.",
        "```sh\nnpm install thing\n```\n\nInstall the package first.",
    )
    for arm in ("explicit", "implicit"):
        page = path / "corpus" / arm / "page.mdx"
        page.write_text(
            page.read_text().replace(
                "Install the package first.",
                source.split("---\n")[2].split("\n\n")[0]
                + "\n\nInstall the package first.",
            )
        )
    summary = run(
        path,
        rejected(first) + accepted(second, host_from="npm install thing") + RELATION,
    )
    assert any("inside a code block" in error for error in summary["errors"])


def test_recompiling_is_idempotent(workspace):
    path, (first, second) = workspace
    text = rejected(first) + accepted(second) + RELATION
    run(path, text, write=True)
    instances = path / "instruments" / "instances.csv"
    once = instances.read_bytes()
    run(path, text, write=True)
    assert instances.read_bytes() == once
    assert once.count(b"reviewed 2026-09-23") == 2
