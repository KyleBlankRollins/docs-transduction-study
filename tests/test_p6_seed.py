"""P6 tests: coding-order seed (``seed.py``) and probe sheet (``probe_sheet.py``)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from docs_transduction_study import probe_sheet, seed


class TestSeed:
    def test_generate_writes_64_hex(self, tmp_path: Path) -> None:
        target = tmp_path / "seed"
        result = seed.write_seed(path=target, design_md=tmp_path / "DESIGN.md")
        assert re.fullmatch(r"[0-9a-f]{64}", result)
        assert target.read_text(encoding="utf-8").strip() == result

    def test_checksum_prefix(self) -> None:
        # The 16-hex checksum prefix matches the harness's _unlock_mapping form.
        assert re.fullmatch(r"[0-9a-f]{16}", seed._checksum("a" * 64))

    def test_refuses_overwrite(self, tmp_path: Path) -> None:
        target = tmp_path / "seed"
        target.write_text("x\n", encoding="utf-8")
        with pytest.raises(SystemExit):
            seed.write_seed(path=target, design_md=tmp_path / "DESIGN.md")

    def test_force_overwrites_when_unlocked(self, tmp_path: Path) -> None:
        target = tmp_path / "seed"
        target.write_text("x\n", encoding="utf-8")
        result = seed.write_seed(
            path=target, force=True, design_md=tmp_path / "DESIGN.md"
        )
        assert target.read_text(encoding="utf-8").strip() == result

    def test_refuses_when_locked(self, tmp_path: Path) -> None:
        design = tmp_path / "DESIGN.md"
        design.write_text('instrument_locked: "2026-09-08"\n', encoding="utf-8")
        target = tmp_path / "seed"
        with pytest.raises(SystemExit):
            seed.write_seed(path=target, design_md=design)
        assert not target.exists()

    def test_force_does_not_bypass_lock(self, tmp_path: Path) -> None:
        design = tmp_path / "DESIGN.md"
        design.write_text('instrument_locked: "2026-09-08"\n', encoding="utf-8")
        target = tmp_path / "seed"
        with pytest.raises(SystemExit):
            seed.write_seed(path=target, force=True, design_md=design)
        assert not target.exists()


class TestProbeSheet:
    def test_build_sheet_lists_instances_and_host_passages(
        self, tmp_path: Path
    ) -> None:
        instances = tmp_path / "instances.csv"
        instances.write_text(
            "instance_id,specimen_id,relation_type,demark_rule,"
            "anchor_explicit,anchor_implicit,host_passage_explicit,"
            "host_passage_implicit,notes\n"
            "S01-R1-001,S01,R1,D1,anchor a,anchor a,"
            "run the first command,run the first command,\n",
            encoding="utf-8",
        )
        specimens = tmp_path / "specimens.csv"
        specimens.write_text(
            "specimen_id,source_path,diataxis_type,"
            "last_major_change_version,selection_rationale\n"
            "S01,guides/page.mdx,tutorial,v7,fixture\n",
            encoding="utf-8",
        )
        out = tmp_path / "sheet.md"
        probe_sheet.build_sheet(instances, specimens, out)
        text = out.read_text(encoding="utf-8")
        assert "## S01 — guides/page.mdx" in text
        assert "### S01-R1-001" in text
        assert "run the first command" in text
        assert "## S01 — guides/page.mdx" in text
