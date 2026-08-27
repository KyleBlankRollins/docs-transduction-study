from pathlib import Path

from docs_transduction_study.corpus_report import count_page, scan_corpus, write_report


def test_count_page_counts_registered_constructs(tmp_path: Path) -> None:
    source = tmp_path / "page.mdx"
    source.write_text(
        """<Steps>\n<Tabs>\n:::note\nMUST and SHOULD\n:::\n\n| one | two |\n| --- | --- |\n""",
        encoding="utf-8",
    )

    counts = count_page(source, tmp_path)

    assert counts.steps_count == 1
    assert counts.tabs_count == 1
    assert counts.aside_count == 1
    assert counts.tables_count == 1
    assert counts.normative_keywords_count == 2


def test_scan_and_report_are_sorted_and_csv_is_stable(tmp_path: Path) -> None:
    source_root = tmp_path / "en"
    (source_root / "z").mkdir(parents=True)
    (source_root / "a.mdx").write_text("MUST", encoding="utf-8")
    (source_root / "z" / "b.md").write_text("MAY", encoding="utf-8")
    (source_root / "pilot.txt").write_text("MUST", encoding="utf-8")
    output = tmp_path / "report.csv"

    write_report(scan_corpus(source_root), output)

    assert output.read_text(encoding="utf-8").splitlines() == [
        "source_path,steps_count,tabs_count,aside_count,prereq_count,tables_count,normative_keywords_count",
        "a.mdx,0,0,0,0,0,1",
        "z/b.md,0,0,0,0,0,1",
    ]
