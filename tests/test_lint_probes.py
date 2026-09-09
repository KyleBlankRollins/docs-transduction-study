"""P6 tests: the probe linter (``lint_probes.py``)."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

from docs_transduction_study import lint_probes
from docs_transduction_study.lint_probes import (
    _is_absence_like,
    _parse_bool,
    lint,
)

PROBES_HEADER = [
    "probe_id",
    "instance_id",
    "question",
    "correct_answer",
    "foil_1",
    "foil_2",
    "version_change",
    "superseded_answer",
    "superseded_source",
]
EXCLUSIONS_HEADER = ["instance_id", "reason", "failed_arm", "date"]
INSTANCES_HEADER = [
    "instance_id",
    "specimen_id",
    "relation_type",
    "anchor_explicit",
    "anchor_implicit",
    "host_passage_explicit",
    "host_passage_implicit",
    "demark_rule",
    "notes",
]
SPECIMENS_HEADER = [
    "specimen_id",
    "source_path",
    "diataxis_type",
    "last_major_change_version",
    "selection_rationale",
]

EXPLICIT_TEXT = (
    "Install the CLI, then run the steps in order. "
    "The commands are alternatives to each other."
)
IMPLICIT_TEXT = EXPLICIT_TEXT


def _write_csv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _fixture(
    tmp_path: Path,
    instances: list[dict[str, str]],
    probes: list[dict[str, str]] | None = None,
    exclusions: list[dict[str, str]] | None = None,
    explicit_text: str = EXPLICIT_TEXT,
    implicit_text: str = IMPLICIT_TEXT,
) -> dict[str, Path]:
    """Write a minimal instrument tree and return the paths lint() wants."""
    probes = [] if probes is None else probes
    exclusions = [] if exclusions is None else exclusions

    _write_csv(tmp_path / "instances.csv", INSTANCES_HEADER, instances)
    _write_csv(tmp_path / "probes.csv", PROBES_HEADER, probes)
    _write_csv(tmp_path / "gate_exclusions.csv", EXCLUSIONS_HEADER, exclusions)
    _write_csv(
        tmp_path / "specimens.csv",
        SPECIMENS_HEADER,
        [
            {
                "specimen_id": "S01",
                "source_path": "page.mdx",
                "diataxis_type": "tutorial",
                "last_major_change_version": "v7",
                "selection_rationale": "fixture",
            }
        ],
    )

    explicit = tmp_path / "explicit"
    implicit = tmp_path / "implicit"
    explicit.mkdir()
    implicit.mkdir()
    (explicit / "page.mdx").write_text(explicit_text, encoding="utf-8")
    (implicit / "page.mdx").write_text(implicit_text, encoding="utf-8")

    return {
        "instances_path": tmp_path / "instances.csv",
        "probes_path": tmp_path / "probes.csv",
        "exclusions_path": tmp_path / "gate_exclusions.csv",
        "specimens_path": tmp_path / "specimens.csv",
        "explicit_dir": explicit,
        "implicit_dir": implicit,
    }


def _probe(iid: str = "S01-R1-001", **overrides: str) -> dict[str, str]:
    row = {
        "probe_id": f"PR-{iid}",
        "instance_id": iid,
        "question": "Are the commands steps to run in order or alternatives?",
        "correct_answer": "Steps to run in order",
        "foil_1": "Alternatives - choose exactly one",
        "foil_2": "",
        "version_change": "false",
        "superseded_answer": "",
        "superseded_source": "",
    }
    row.update(overrides)
    return row


def _instance(iid: str = "S01-R1-001") -> dict[str, str]:
    return {
        "instance_id": iid,
        "specimen_id": "S01",
        "relation_type": "R1",
        "anchor_explicit": "run the steps",
        "anchor_implicit": "run the steps",
        "host_passage_explicit": EXPLICIT_TEXT,
        "host_passage_implicit": IMPLICIT_TEXT,
        "demark_rule": "D1",
        "notes": "",
    }


class TestParseBool:
    def test_true_variants(self) -> None:
        assert _parse_bool("true") is True
        assert _parse_bool("TRUE") is True
        assert _parse_bool("1") is True
        assert _parse_bool("yes") is True

    def test_false_variants_and_empty(self) -> None:
        assert _parse_bool("false") is False
        assert _parse_bool("0") is False
        assert _parse_bool("") is False
        assert _parse_bool(None) is False

    def test_malformed(self) -> None:
        assert _parse_bool("maybe") is None


class TestAbsenceLike:
    def test_relation_is_not_absent(self) -> None:
        assert not _is_absence_like("Sequence - run all three in order")

    def test_absence_phrases(self) -> None:
        assert _is_absence_like("The text does not say")
        assert _is_absence_like("the document does not mention this")
        assert _is_absence_like("The requirement is not stated")
        assert _is_absence_like("nothing about it is described")


class TestCoverage:
    def test_valid_one_to_one(self, tmp_path: Path) -> None:
        paths = _fixture(tmp_path, [_instance()], [_probe()])
        report = lint(**paths)
        assert report.count == 0

    def test_exclusion_substitutes_probe(self, tmp_path: Path) -> None:
        paths = _fixture(
            tmp_path,
            [_instance()],
            probes=[],
            exclusions=[
                {
                    "instance_id": "S01-R1-001",
                    "reason": "propositional-equivalence gate failed",
                    "failed_arm": "implicit",
                    "date": "2026-09-08",
                }
            ],
        )
        report = lint(**paths)
        assert report.count == 0

    def test_missing_probe_and_exclusion(self, tmp_path: Path) -> None:
        paths = _fixture(tmp_path, [_instance()], probes=[])
        report = lint(**paths)
        assert any("no probe and no exclusion" in e for e in report.errors)

    def test_duplicate_probe(self, tmp_path: Path) -> None:
        paths = _fixture(tmp_path, [_instance()], [_probe(), _probe(probe_id="PR-dup")])
        report = lint(**paths)
        assert any("2 probes" in e for e in report.errors)

    def test_probe_and_exclusion_conflict(self, tmp_path: Path) -> None:
        paths = _fixture(
            tmp_path,
            [_instance()],
            [_probe()],
            exclusions=[
                {
                    "instance_id": "S01-R1-001",
                    "reason": "gate",
                    "failed_arm": "explicit",
                    "date": "2026-09-08",
                }
            ],
        )
        report = lint(**paths)
        assert any("both a probe and an exclusion" in e for e in report.errors)

    def test_unknown_instance_in_probe(self, tmp_path: Path) -> None:
        paths = _fixture(tmp_path, [_instance()], [_probe(iid="S99-X")])
        report = lint(**paths)
        assert any("unknown" in e for e in report.errors)

    def test_multi_instance_equality(self, tmp_path: Path) -> None:
        paths = _fixture(
            tmp_path,
            [_instance(), _instance("S01-R2-001")],
            probes=[_probe(), _probe("S01-R2-001")],
        )
        report = lint(**paths)
        assert report.count == 0


class TestExclusions:
    def test_missing_fields_flagged(self, tmp_path: Path) -> None:
        paths = _fixture(
            tmp_path,
            [_instance()],
            probes=[],
            exclusions=[
                {
                    "instance_id": "S01-R1-001",
                    "reason": "",
                    "failed_arm": "",
                    "date": "",
                }
            ],
        )
        report = lint(**paths)
        assert any("no reason" in e for e in report.errors)
        assert any("no failed_arm" in e for e in report.errors)
        assert any("no date" in e for e in report.errors)


class TestDistinctiveStrings:
    def test_verbatim_in_explicit(self, tmp_path: Path) -> None:
        probe = _probe(correct_answer="The commands are alternatives to each other.")
        paths = _fixture(tmp_path, [_instance()], [probe])
        report = lint(**paths)
        assert any("explicit A0" in e for e in report.errors)

    def test_verbatim_in_implicit(self, tmp_path: Path) -> None:
        probe = _probe(correct_answer="The commands are alternatives to each other.")
        paths = _fixture(
            tmp_path,
            [_instance()],
            [probe],
            implicit_text=probe["correct_answer"],
        )
        report = lint(**paths)
        assert any("implicit A0" in e for e in report.errors)

    def test_distinct_answer_ok(self, tmp_path: Path) -> None:
        probe = _probe(correct_answer="The order is fixed and must be held")
        paths = _fixture(tmp_path, [_instance()], [probe])
        report = lint(**paths)
        assert report.count == 0


class TestFoils:
    def test_absence_like_flagged(self, tmp_path: Path) -> None:
        probe = _probe(foil_1="The text does not say what the relation is")
        paths = _fixture(tmp_path, [_instance()], [probe])
        report = lint(**paths)
        assert any("paraphrases absence" in e for e in report.errors)

    def test_foil_duplicates_answer(self, tmp_path: Path) -> None:
        answer = "Steps to run in order"
        probe = _probe(correct_answer=answer, foil_1=answer)
        paths = _fixture(tmp_path, [_instance()], [probe])
        report = lint(**paths)
        assert any("duplicates correct_answer" in e for e in report.errors)

    def test_empty_foil_1_rejected(self, tmp_path: Path) -> None:
        probe = _probe(foil_1="", foil_2="")
        paths = _fixture(tmp_path, [_instance()], [probe])
        report = lint(**paths)
        assert any("no foil_1" in e for e in report.errors)


class TestVersionChange:
    def test_vc_true_without_superseded(self, tmp_path: Path) -> None:
        probe = _probe(version_change="true")
        paths = _fixture(tmp_path, [_instance()], [probe])
        report = lint(**paths)
        assert any("superseded_answer" in e for e in report.errors)
        assert any("superseded_source" in e for e in report.errors)

    def test_vc_true_with_superseded_passes(self, tmp_path: Path) -> None:
        probe = _probe(
            version_change="true",
            superseded_answer="Use the old flag",
            superseded_source="docs @ 6eca24e (pre-change SHA)",
        )
        paths = _fixture(tmp_path, [_instance()], [probe])
        report = lint(**paths)
        assert report.count == 0

    def test_vc_false_with_superseded_incoherent(self, tmp_path: Path) -> None:
        probe = _probe(
            version_change="false",
            superseded_answer="Use the old flag",
            superseded_source="docs",
        )
        paths = _fixture(tmp_path, [_instance()], [probe])
        report = lint(**paths)
        assert any("incoherent" in e for e in report.errors)

    def test_malformed_bool(self, tmp_path: Path) -> None:
        probe = _probe(version_change="banana")
        paths = _fixture(tmp_path, [_instance()], [probe])
        report = lint(**paths)
        assert any("must be a boolean" in e for e in report.errors)


class TestSchema:
    def test_missing_probe_header(self, tmp_path: Path) -> None:
        paths = _fixture(tmp_path, [_instance()], [_probe()])
        header = [h for h in PROBES_HEADER if h != "version_change"]
        rows = [{k: v for k, v in _probe().items() if k in header}]
        _write_csv(paths["probes_path"], header, rows)
        report = lint(**paths)
        assert any("missing required columns" in e for e in report.errors)

    def test_empty_exclusions_file_is_valid(self, tmp_path: Path) -> None:
        paths = _fixture(tmp_path, [_instance()], [_probe()])
        paths["exclusions_path"].write_text(
            "instance_id,reason,failed_arm,date\n", encoding="utf-8"
        )
        report = lint(**paths)
        assert report.count == 0


def test_main_exits_nonzero_on_unlocked_instrument(tmp_path: Path) -> None:
    """The CLI must exit 1 while the instrument is not lockable."""
    paths = _fixture(tmp_path, [_instance()], probes=[])
    old_argv = sys.argv
    sys.argv = [
        "lint_probes",
        "--instances",
        str(paths["instances_path"]),
        "--probes",
        str(paths["probes_path"]),
        "--gate-exclusions",
        str(paths["exclusions_path"]),
        "--specimens",
        str(paths["specimens_path"]),
        "--explicit-dir",
        str(paths["explicit_dir"]),
        "--implicit-dir",
        str(paths["implicit_dir"]),
    ]
    try:
        with pytest.raises(SystemExit) as exc:
            lint_probes.main()
        assert exc.value.code == 1
    finally:
        sys.argv = old_argv
