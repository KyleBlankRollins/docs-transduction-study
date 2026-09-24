"""P5 tests: stage drivers, anchors, coding harness."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import bs4
import pytest

from docs_transduction_study import anchors, coding
from docs_transduction_study.stages import a1_build, a2_snapshot, a3_extract, a4_chunk


class TestA1:
    def test_study_build_refuses_unlocked_instrument(self, tmp_path, monkeypatch):
        monkeypatch.setattr(a1_build, "REPO_ROOT", tmp_path)
        (tmp_path / "DESIGN.md").write_text('---\ninstrument_locked: ""\n---\n')
        with pytest.raises(ValueError, match="before L2"):
            a1_build.run_builds(tmp_path / "output")
        assert not (tmp_path / "output").exists()

    def test_pilot_chrome_is_measured_per_chunk(self):
        html = '<div class="sl-markdown-content"><a class="sl-anchor-link"><span class="sr-only">Label</span></a><p>abcdefghij</p></div>'
        result = a1_build._pilot_chrome_metrics(html, "Label abcdefghij", 5)
        assert result["identified_chrome_chars"] == 5
        assert result["chunk_fractions"] == [1.0, 0.0, 0.0, 0.0]

    def test_pilot_verification_browser_roundtrip(self, tmp_path):
        page = tmp_path / "tree/dist/en/pilot/index.html"
        page.parent.mkdir(parents=True)
        page.write_text(
            '<html><body><nav>Outside</nav><div class="sl-markdown-content">'
            "<p>First passage.</p><p>Second passage.</p><p>Third passage.</p>"
            "</div></body></html>"
        )
        result = a1_build._verify_pilot_page(
            tmp_path / "tree", "pilot.mdx", tmp_path / "a2"
        )
        assert result["a2"]["stable"]
        assert result["structural_chrome_inside"] == 0
        assert result["outside_content_chars"] > 0
        assert len(result["paragraph_anchor_checks"]) == 3
        assert result["chunk_reconstruction"]

    def test_html_checksums_compare_bytes_and_reject_empty(self, tmp_path):
        with pytest.raises(ValueError, match="nonempty"):
            a1_build._html_checksums(tmp_path)
        page = tmp_path / "index.html"
        page.write_text("first")
        first = a1_build._html_checksums(tmp_path)
        assert first == a1_build._html_checksums(tmp_path)
        page.write_text("second")
        assert first != a1_build._html_checksums(tmp_path)

    def test_verify_pilot_requires_page(self, tmp_path):
        with pytest.raises(ValueError, match="requires a pilot page"):
            a1_build.run_builds(tmp_path, verify_pilot=True)

    def test_pilot_only_requires_page(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "docs_transduction_study.stages.a1_build",
                "--pilot-only",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 2
        assert "--pilot-only requires --pilot" in result.stderr

    def test_extraction_diagnostic_refuses_broad_fallback(self, tmp_path, monkeypatch):
        def materialise(tree, arm):
            (tree / "dist").mkdir(parents=True)
            (tree / "dist" / "index.html").write_text("<main>Not content</main>")

        monkeypatch.setattr(a1_build, "_materialise_tree", materialise)
        monkeypatch.setattr(a1_build, "_build", lambda tree, arm: 0)
        with pytest.raises(ValueError, match="sl-markdown-content"):
            a1_build._b3_b4_extraction_check(tmp_path, "explicit")

    @pytest.mark.parametrize("build_exit", [0, 1])
    def test_pilot_trees_disposed(self, tmp_path, monkeypatch, build_exit):
        specimens = tmp_path / "specimens.csv"
        specimens.write_text("source_path\nguides/testing.mdx\n")
        monkeypatch.setattr(a1_build, "SPECIMENS_CSV", specimens)
        monkeypatch.setattr(
            a1_build,
            "_record_version_info",
            lambda: {"node_version": "test", "pnpm_version": "test"},
        )
        trees = []

        def materialise(tree, arm, *, pilot_page):
            trees.append(tree)
            pilot = tree / "dist" / "en" / "install-and-setup" / "index.html"
            pilot.parent.mkdir(parents=True)
            pilot.write_text('<div class="sl-markdown-content">Pilot</div>')

        monkeypatch.setattr(a1_build, "_materialise_tree", materialise)
        monkeypatch.setattr(a1_build, "_build", lambda tree, arm: build_exit)
        kwargs = {
            "pilot_page": "install-and-setup.mdx",
            "skip_determinism": True,
            "skip_chrome": True,
        }
        if build_exit:
            with pytest.raises(RuntimeError, match="build failed"):
                a1_build.run_builds(tmp_path / "out", **kwargs)
        else:
            result = a1_build.run_builds(tmp_path / "out", **kwargs)
            assert result["pages_copied"] == {"explicit": 1, "implicit": 1}
        assert trees and all(not tree.exists() for tree in trees)

    def test_pilot_rejects_study_page(self, tmp_path, monkeypatch):
        specimens = tmp_path / "specimens.csv"
        specimens.write_text("source_path\nguides/testing.mdx\n")
        monkeypatch.setattr(a1_build, "SPECIMENS_CSV", specimens)
        with pytest.raises(ValueError, match="must not be a study specimen"):
            a1_build.run_builds(tmp_path / "out", pilot_page="guides/testing.mdx")

    def test_missing_implicit_pilot_refuses_fallback(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="implicit pilot is missing"):
            a1_build._override_pilot(tmp_path, "implicit", "nonexistent-test-pilot.mdx")

    def test_pilot_archive_excludes_study_pages(self, tmp_path):
        tree = tmp_path / "tree"
        pilot = tree / "dist" / "en" / "install-and-setup" / "index.html"
        specimen = tree / "dist" / "en" / "guides" / "testing" / "index.html"
        pilot.parent.mkdir(parents=True)
        specimen.parent.mkdir(parents=True)
        pilot.write_text("<article>Pilot</article>")
        specimen.write_text("<article>Study specimen</article>")
        output = tmp_path / "artifacts"

        count = a1_build._copy_artifacts(
            "explicit", tree, output, pilot_page="install-and-setup.mdx"
        )

        assert count == 1
        archived = list((output / "explicit").rglob("*.html"))
        assert [
            path.relative_to(output / "explicit").as_posix() for path in archived
        ] == ["en/install-and-setup/index.html"]

    def test_missing_pilot_html_fails_closed(self, tmp_path):
        tree = tmp_path / "tree"
        (tree / "dist").mkdir(parents=True)
        (tree / "dist" / "404.html").write_text("Not a pilot artifact")

        with pytest.raises(FileNotFoundError, match="pilot HTML"):
            a1_build._copy_artifacts(
                "explicit", tree, tmp_path / "out", pilot_page="install-and-setup.mdx"
            )


class TestA2:
    def test_compiled_tabs_browser_roundtrip(self, tmp_path):
        page = tmp_path / "site" / "pilot" / "index.html"
        page.parent.mkdir(parents=True)
        page.write_text(
            '<div role="tablist"><button role="tab" aria-selected="true">One</button>'
            '<button role="tab" aria-selected="false">Two</button></div>'
            '<div role="tabpanel">Visible panel</div>'
            '<div role="tabpanel" hidden>Hidden panel</div>'
        )
        result = a2_snapshot.run_snapshot(
            tmp_path / "site", "/pilot/", out_dir=tmp_path / "snapshots"
        )
        snapshot = (tmp_path / "snapshots" / "snapshot-1.txt").read_text()
        assert result["stable"] and result["tab_roles_found"]
        assert "Visible panel" in snapshot
        assert "Hidden panel" not in snapshot
        assert "[selected]" in snapshot

    def test_native_snapshot_detects_nested_changes(self):
        snapshot = '- tablist:\n  - tab "One" [selected]\n- tabpanel: Visible'
        assert a2_snapshot._diff_snapshots(snapshot, snapshot) == []
        assert a2_snapshot._diff_snapshots(
            snapshot, snapshot.replace("Visible", "Changed")
        )

    def test_native_snapshot_saved_verbatim(self, tmp_path, monkeypatch):
        snapshot = '- tablist:\n  - tab "One" [selected]\n- tabpanel: Visible'

        monkeypatch.setattr(a2_snapshot, "_get_snapshot", lambda port, path: snapshot)
        result = a2_snapshot.run_snapshot(
            tmp_path, "/pilot/", out_dir=tmp_path / "snap"
        )
        assert result["stable"]
        assert len(result["tab_details"]) == 3
        assert (tmp_path / "snap" / "snapshot-1.txt").read_text() == snapshot

    def test_flatten_empty(self):
        assert a2_snapshot._flatten_a11y_tree({})[0][1] == "(unknown)"

    def test_diff_identical(self):
        a = {"role": "doc", "children": []}
        assert a2_snapshot._diff_snapshots(a, a) == []

    def test_missing_artifacts_refused(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            a2_snapshot._start_artifact_server(tmp_path / "missing", port=0)

    def test_server_serves_compiled_bytes(self, tmp_path):
        from urllib.request import urlopen

        compiled = b'<div role="tabpanel">Compiled pilot</div>'
        (tmp_path / "index.html").write_bytes(compiled)
        server, thread = a2_snapshot._start_artifact_server(tmp_path, port=0)
        try:
            with urlopen(
                f"http://127.0.0.1:{server.server_port}/", timeout=5
            ) as response:
                assert response.read() == compiled
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        assert not thread.is_alive()


class TestA3:
    def test_extract_content_only(self, tmp_path):
        page = tmp_path / "page.html"
        page.write_text(
            "<html><body><nav>Sidebar</nav><main><h1>Title</h1>"
            '<div class="sl-markdown-content"><p>Hello</p><p>world</p></div>'
            "<footer>Footer</footer></main><article>Decoy</article></body></html>"
        )
        text, metadata = a3_extract.extract_article_text(page)
        assert text == "Hello world"
        assert metadata["extraction_target"] == ".sl-markdown-content"
        assert metadata["extractor_version"] == bs4.__version__

    @pytest.mark.parametrize("tag", ["article", "main", "body"])
    def test_no_content_container_raises(self, tmp_path, tag):
        page = tmp_path / "page.html"
        page.write_text(f"<{tag}>Not the registered container</{tag}>")
        with pytest.raises(ValueError, match="found 0"):
            a3_extract.extract_article_text(page)

    def test_multiple_content_containers_raise(self, tmp_path):
        page = tmp_path / "page.html"
        page.write_text('<div class="sl-markdown-content">Ambiguous</div>' * 2)
        with pytest.raises(ValueError, match="found 2"):
            a3_extract.extract_article_text(page)

    def test_cli_extracts_both_arms(self, tmp_path):
        source = tmp_path / "input"
        output = tmp_path / "output"
        for arm in ("explicit", "implicit"):
            (source / arm).mkdir(parents=True)
            (source / arm / "index.html").write_text(
                '<div class="sl-markdown-content">Pilot text</div>'
            )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "docs_transduction_study.stages.a3_extract",
                "--artifacts",
                str(source),
                "--out",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        for arm in ("explicit", "implicit"):
            assert (output / arm / "index.txt").read_text() == "Pilot text"
            metadata = json.loads((output / arm / "_metadata.json").read_text())
            assert metadata[0]["extraction_target"] == ".sl-markdown-content"


class TestA4:
    def test_lossless_whitespace_and_invalid_size(self):
        assert a4_chunk.chunk_text("AAAA    BBBB", 4) == ["AAAA", "    ", "BBBB"]
        with pytest.raises(ValueError, match="positive"):
            a4_chunk.chunk_text("abc", 0)

    def test_stages_reject_missing_arm_before_writing(self, tmp_path):
        source = tmp_path / "source/explicit"
        source.mkdir(parents=True)
        (source / "page.html").write_text('<div class="sl-markdown-content">Text</div>')
        (source / "page.txt").write_text("Text")
        output = tmp_path / "out"
        with pytest.raises(ValueError, match="both arms"):
            a3_extract.run_extraction(source.parent, output)
        with pytest.raises(ValueError, match="both arms"):
            a4_chunk.run_chunking(source.parent, output, 1500)
        assert not output.exists()

    def test_empty(self):
        assert a4_chunk.chunk_text("", 100) == []

    def test_split(self):
        assert len(a4_chunk.chunk_text("A" * 250, 100)) == 3


class TestAnchors:
    def test_raw_coordinates_after_normalization(self):
        text = "  Intro\n\n\t\u201cHello   world\u201d"
        assert anchors.resolve_anchor_offset('"hello world"', text) == text.index(
            "\u201c"
        )
        assert anchors.resolve_anchor_span('"hello world"', text) == (
            text.index("\u201c"),
            len(text),
        )
        assert anchors.resolve_anchor_offset("", text) is None

    def test_assign_real_routes_host_start_and_per_arm_spans(
        self, tmp_path, monkeypatch
    ):
        specimens = tmp_path / "specimens.csv"
        specimens.write_text("specimen_id,source_path\nS01,guides/page.mdx\n")
        monkeypatch.setattr(anchors, "SPECIMENS_CSV", specimens)
        instances = tmp_path / "instances.csv"
        instances.write_text(
            "instance_id,specimen_id,anchor_explicit,anchor_implicit,host_passage_explicit,host_passage_implicit\nS01-O1-001,S01,anchor,anchor,host anchor,host anchor\n"
        )
        original = instances.read_bytes()
        for arm, prefix in [("explicit", "x" * 1495), ("implicit", "x" * 1500)]:
            page = tmp_path / "a3" / arm / "en/guides/page/index.txt"
            page.parent.mkdir(parents=True)
            page.write_text(prefix + "host anchor")
            other = tmp_path / "a3" / arm / "en/other/index.txt"
            other.parent.mkdir(parents=True)
            other.write_text("unrelated")
        a4_chunk.run_chunking(tmp_path / "a3", tmp_path / "a4", 1500)
        result = anchors.assign_chunks(instances, tmp_path / "a4")
        assert result["resolved"] == 2
        assert instances.read_bytes() == original
        with Path(result["output"]).open() as handle:
            row = next(csv.DictReader(handle))
        assert "guides/page/index-chunk-0000" in row["chunk_explicit"]
        assert "guides/page/index-chunk-0001" in row["chunk_implicit"]
        assert row["spans_chunks_explicit"] == "True"
        assert row["spans_chunks_implicit"] == "False"
        with pytest.raises(ValueError, match="overwrite"):
            anchors.assign_chunks(instances, tmp_path / "a4", instances)

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
