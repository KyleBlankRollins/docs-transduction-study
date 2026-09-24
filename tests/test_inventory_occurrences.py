import pytest

from docs_transduction_study.inventory import (
    Instance,
    surface_o_candidates,
    write_instances_csv,
)
from docs_transduction_study.review_o1_o2 import occurrence_context, pair_occurrences


def test_cross_arm_occurrence_pairing_preserves_repeats_and_title():
    explicit = ":::note[Fail the test]\nUse the file. Then the file.\n:::"
    implicit = "Fail the test: Use the file. Then the file."
    expressions = ["the test", "the file", "the file"]
    spans = []
    cursor = 0
    for expression in expressions:
        start = explicit.index(expression, cursor)
        cursor = start + len(expression)
        spans.append((start, cursor))
    paired = pair_occurrences(explicit, implicit, spans)
    assert [implicit[start:end] for start, end in paired] == expressions
    assert paired[1] != paired[2]
    with pytest.raises(ValueError, match="cross-arm review"):
        pair_occurrences(explicit, "unrelated", spans)


def test_context_uses_requested_occurrence():
    text = "First the file.\nSecond the file."
    start = text.rindex("the file")
    context = occurrence_context(text, "the file", f"A0 chars [{start},{start + 8})")
    assert context["source_line"] == "2"
    assert context["before"].endswith("Second")
    with pytest.raises(ValueError, match="do not match"):
        occurrence_context(text, "other", f"A0 chars [{start},{start + 8})")


def test_legacy_inventory_cannot_be_silently_merged(tmp_path):
    output = tmp_path / "instances.csv"
    write_instances_csv([Instance("S01-O1-001", "S01", "O1")], output)
    before = output.read_bytes()
    with pytest.raises(ValueError, match="legacy"):
        write_instances_csv([Instance("S01-O1-at-000010", "S01", "O1")], output)
    assert output.read_bytes() == before


def test_repeated_expressions_are_distinct_occurrences(tmp_path):
    specimens = tmp_path / "specimens.csv"
    specimens.write_text("specimen_id,source_path\nS01,page.mdx\n")
    source = '---\ntitle: the file\n---\nimport Thing from "the file";\nThe file. The file. See this step. See this step.\n'
    (tmp_path / "page.mdx").write_text(source)
    candidates = surface_o_candidates(specimens, tmp_path, tmp_path)
    references = [row for row in candidates if row.relation_type == "O1"]
    deixis = [row for row in candidates if row.relation_type == "O2"]
    assert len(references) == len(deixis) == 2
    assert len({row.instance_id for row in candidates}) == 4
    assert all("-at-" in row.instance_id for row in candidates)
    first_offset = source.index("The file")
    assert (
        f"A0 chars [{first_offset},{first_offset + len('The file')})"
        in references[0].notes
    )


def test_embedded_astro_frontmatter_does_not_mask_document(tmp_path):
    specimens = tmp_path / "specimens.csv"
    specimens.write_text("specimen_id,source_path\nS01,page.mdx\n")
    (tmp_path / "page.mdx").write_text(
        "---\ntitle: Example\n---\n```astro\n---\n---\n```\nThe file.\n---\n"
    )
    candidates = surface_o_candidates(specimens, tmp_path, tmp_path)
    assert len(candidates) == 1
    assert "'The file'" in candidates[0].notes
