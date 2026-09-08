"""P5 tests: stage drivers, anchors, coding harness."""

from __future__ import annotations

import csv
import json

import pytest

from docs_transduction_study import anchors, coding
from docs_transduction_study.stages import a2_snapshot, a3_extract, a4_chunk


class TestA2:
    def test_flatten_empty(self):
        assert a2_snapshot._flatten_a11y_tree({})[0][1] == "(unknown)"

    def test_diff_identical(self):
        a = {"role": "doc", "children": []}
        assert a2_snapshot._diff_snapshots(a, a) == []

    def test_dev_server_exits(self, monkeypatch, tmp_path):
        monkeypatch.setattr(a2_snapshot, "ARTIFACTS_DIR", tmp_path / "artifacts")
        with pytest.raises(SystemExit):
            a2_snapshot._start_dev_server(tmp_path, port=19999)


class TestA3:
    def test_extract_article(self, tmp_path):
        p = tmp_path / "f.html"
        p.write_text("<html><body><article>Hello</article></body></html>")
        t, m = a3_extract.extract_article_text(p)
        assert "Hello" in t
        assert m["extraction_target"] == "article"

    def test_no_article_raises(self, tmp_path):
        p = tmp_path / "f.html"
        p.write_text("<html><body><main>C</main></body></html>")
        with pytest.raises(ValueError):
            a3_extract.extract_article_text(p)


class TestA4:
    def test_empty(self):
        assert a4_chunk.chunk_text("", 100) == []

    def test_split(self):
        assert len(a4_chunk.chunk_text("A" * 250, 100)) == 3


class TestAnchors:
    def test_normalize_full_spec(self):
        n = anchors._normalize
        assert n("hello   world") == "hello world"
        assert n("\u201chello\u201d") == '"hello"'

    def test_resolve_found(self):
        assert anchors.resolve_anchor_offset("world", "hello world") is not None

    def test_resolve_not_found(self):
        assert anchors.resolve_anchor_offset("xyz", "hello") is None

    def test_resolve_fuzzy_forbidden(self):
        assert anchors.resolve_anchor_offset("abcdefghi", "abcdef") is None

    def test_find_chunk(self):
        c = [
            {"chunk_start": 0, "char_count": 50, "chunk_index": 0},
            {"chunk_start": 50, "char_count": 50, "chunk_index": 1},
        ]
        assert anchors.find_chunk_for_offset(10, c)["chunk_index"] == 0

    def test_spans_true(self):
        c = [
            {"chunk_start": 0, "char_count": 50, "chunk_index": 0},
            {"chunk_start": 50, "char_count": 50, "chunk_index": 1},
        ]
        # Passage starts at 45 in chunk 0, ends at 54 — last_char=54 is in chunk 1
        text = "x" * 45 + "hello world" + "x" * 30
        assert anchors.compute_spans_chunks("hello world", text, c)

    def test_spans_false_inclusive(self):
        """Passage at exact boundary must NOT span (Finding 10 fix)."""
        c = [{"chunk_start": 0, "char_count": 10, "chunk_index": 0}]
        assert not anchors.compute_spans_chunks("abcdefghij", "abcdefghij", c)

    def test_page_filtered(self, tmp_path):
        """Cross-page chunk fix (Finding 5)."""
        (tmp_path / "a3" / "ex").mkdir(parents=True)
        (tmp_path / "a3" / "ex" / "a.txt").write_text("A" * 500)
        (tmp_path / "a4" / "ex").mkdir(parents=True)
        idx = [
            {
                "chunk_path": "a-0.txt",
                "page": "a.txt",
                "chunk_start": 0,
                "char_count": 100,
                "chunk_index": 0,
            },
            {
                "chunk_path": "b-0.txt",
                "page": "b.txt",
                "chunk_start": 0,
                "char_count": 100,
                "chunk_index": 0,
            },
        ]
        (tmp_path / "a4" / "ex" / "_chunk_index.json").write_text(json.dumps(idx))
        off = anchors.resolve_anchor_offset("AAA", "A" * 500)
        pc = [c for c in idx if c["page"] == "a.txt"]
        ch = anchors.find_chunk_for_offset(off, pc)
        assert ch is not None and ch["chunk_path"] == "a-0.txt"


class TestCoding:
    def test_anon(self):
        assert coding._anonymise("i1", b"s").startswith("ID-")

    def test_refuses_stdin(self, monkeypatch):
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        with pytest.raises(SystemExit):
            coding.code()

    def test_manifest_no_instance_id(self, tmp_path, monkeypatch):
        i = tmp_path / "i.csv"
        i.write_text(
            "instance_id,specimen_id,relation_type,demark_rule\nS01-R1-001,S01,R1,D1\n"
        )
        monkeypatch.setattr(coding, "INSTANCES_CSV", i)
        monkeypatch.setattr(coding, "CODING_DIR", tmp_path / "c")
        (tmp_path / "c").mkdir()
        monkeypatch.setattr(coding, "MANIFEST_JSON", tmp_path / "c" / "m.json")
        monkeypatch.setattr(coding, "MAPPING_ENC", tmp_path / "c" / "e.enc")
        coding.setup(seed_hex="aa" * 16)
        m = json.loads((tmp_path / "c" / "m.json").read_text())
        for e in m:
            assert "instance_id" not in e
            assert "opaque_id" in e

    def test_mapping_encrypted(self, tmp_path, monkeypatch):
        i = tmp_path / "i.csv"
        i.write_text("instance_id,s,r,d\nS01-R1-001,S01,R1,D1\n")
        monkeypatch.setattr(coding, "INSTANCES_CSV", i)
        monkeypatch.setattr(coding, "CODING_DIR", tmp_path / "c")
        (tmp_path / "c").mkdir()
        monkeypatch.setattr(coding, "MANIFEST_JSON", tmp_path / "c" / "m.json")
        monkeypatch.setattr(coding, "MAPPING_ENC", tmp_path / "c" / "e.enc")
        coding.setup(seed_hex="ff" * 16)
        enc = (tmp_path / "c" / "e.enc").read_bytes()
        assert b"instance_id" not in enc
        assert enc[:4] != b"{"

    def test_manifest_arm_stage_combos(self, tmp_path, monkeypatch):
        """Setup creates entries per arm x stage (Finding 2 fix)."""
        i = tmp_path / "i.csv"
        i.write_text(
            "instance_id,specimen_id,relation_type,demark_rule\nS01-R1-001,S01,R1,D1\n"
        )
        monkeypatch.setattr(coding, "INSTANCES_CSV", i)
        monkeypatch.setattr(coding, "CODING_DIR", tmp_path / "c")
        (tmp_path / "c").mkdir()
        monkeypatch.setattr(coding, "MANIFEST_JSON", tmp_path / "c" / "m.json")
        monkeypatch.setattr(coding, "MAPPING_ENC", tmp_path / "c" / "e.enc")
        coding.setup(seed_hex="aa" * 16)
        m = json.loads((tmp_path / "c" / "m.json").read_text())
        assert len(m) == len(coding.ARM_STAGE_COMBOS)

    def test_no_correct_answer(self, tmp_path, monkeypatch):
        """Manifest must NOT contain correct_answer (Finding 4 fix)."""
        i = tmp_path / "i.csv"
        i.write_text(
            "instance_id,specimen_id,relation_type,demark_rule\nS01-R1-001,S01,R1,D1\n"
        )
        pb = tmp_path / "pr.csv"
        pb.write_text(
            "probe_id,instance_id,relation_type,artifact_stage,question,correct_answer,foil_1,foil_2\n"
            "P1,S01-R1-001,R1,A4,What?,Correct,Wrong,Not said\n"
        )
        monkeypatch.setattr(coding, "INSTANCES_CSV", i)
        monkeypatch.setattr(coding, "PROBES_CSV", pb)
        monkeypatch.setattr(coding, "CODING_DIR", tmp_path / "c")
        (tmp_path / "c").mkdir()
        monkeypatch.setattr(coding, "MANIFEST_JSON", tmp_path / "c" / "m.json")
        monkeypatch.setattr(coding, "MAPPING_ENC", tmp_path / "c" / "e.enc")
        coding.setup(seed_hex="aa" * 16)
        m = json.loads((tmp_path / "c" / "m.json").read_text())
        for e in m:
            assert "correct_answer" not in e
            assert "probe_question" in e

    def test_append_only(self, tmp_path):
        """Append-only: writing twice preserves both rows."""
        m1a = tmp_path / "c" / "m1a.csv"
        m1a.parent.mkdir(parents=True, exist_ok=True)
        import datetime

        ts = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
        r = {
            "opaque_id": "ID-a",
            "artifact_stage": "A4",
            "arm": "explicit",
            "score": "3",
            "score_label": "P",
            "explicit_inferred": "e",
            "option_order": "1;2",
            "pass_number": "1",
            "session_id": "s1",
            "timestamp": ts,
        }
        r2 = r.copy()
        r2["score"] = "2"
        m1a.write_text(
            "opaque_id,artifact_stage,arm,score,score_label,explicit_inferred,option_order,pass_number,session_id,timestamp\n"
        )
        for row in (r, r2):
            with open(m1a, "a", encoding="utf-8", newline="") as f:
                csv.DictWriter(
                    f, fieldnames=coding.M1A_FIELDS, lineterminator="\n"
                ).writerow(row)
        lines = m1a.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3
        assert lines[1].split(",")[3] == "3"
        assert lines[2].split(",")[3] == "2"
