# ADR-0004 — License code MIT, study data CC BY 4.0, corpus unchanged

- **Status:** Accepted
- **Date:** 2026-08-02
- **Relates to:** `IMPLEMENTATION_PLAN.md` → D-6; `LICENSE`; `LICENSE-DATA`; `DESIGN.md` → *Corpus*

## Context

The study commits to publishing its coded dataset, logs, and analysis scripts. It
also republishes documentation it did not write, plus mechanically degraded
derivatives of it. Those are three different kinds of material with three
different constraints, and a single repository license would have obscured that.

The corpus constraint is fixed and not ours to choose: Astro's documentation is
MIT licensed, which is what permits publishing specimens and derived variants at
all. MIT travels with the material and with anything derived from it.

## Decision

Three scopes, stated separately:

| Material | License | Why |
| -------- | ------- | --- |
| `src/`, `pipeline/demark/`, `tests/` | **MIT** | Software. Matches the corpus's own terms, so nothing in the repository is more restrictive than the thing it studies. |
| Prose documents, `instruments/`, `coding/`, `logs/`, `figures/` | **CC BY 4.0** | Data and written work. Attribution is the one condition worth keeping on a dataset whose value depends on being traceable to its method. |
| `corpus/`, and corpus text reproduced inside `artifacts/` | **Astro's MIT, unchanged** | Not ours to relicense. |

The third row is the one that needed writing down. It was tempting to describe
the repository as "MIT code, CC BY data" and stop, but pipeline artifacts contain
rendered and extracted corpus text, so a blanket CC BY grant over `artifacts/`
would have purported to relicense Astro's content. The CC BY grant applies to the
study's own contribution — the selection, the transformation, the coding, and the
analysis — not to the underlying documentation.

`corpus/NOTICE` is written at M1, when the corpus is pinned and there is a SHA to
name.

## Consequences

**Nothing in the repository is more restrictive than Astro's own terms**, which
matters because the study republishes their work and criticizes documentation
practice using it as the example.

**The implicit variants need an explicit disclaimer wherever they travel.** They
are derivative works created by this study, mechanically degraded on purpose, and
they are not how Astro's docs are written. Both `LICENSE-DATA` and the README say
so. Someone lifting `corpus/implicit/` out of context would otherwise be
redistributing deliberately-damaged documentation under Astro's name.

**Two license files is slightly more friction** than one, and tooling that
auto-detects a repository license will report MIT and miss the rest. Accepted:
the alternative is a single license that is wrong about at least one of the three
scopes.

### What to watch

- **`corpus/NOTICE` actually gets written at M1.** Until then the corpus scope is
  described in two license files and honored nowhere concrete.
- **Phase 2 logs.** Inspect eval logs carry full transcripts, which will contain
  corpus text passed to models. Same treatment as `artifacts/`.

## Alternatives rejected

- **MIT for everything.** Simpler, but MIT is a software license; applying it to a
  coded dataset and a pre-registration leaves the attribution expectation implicit
  exactly where the study most wants it explicit.
- **CC BY for everything.** Makes the code awkward to reuse and is a poor fit for
  a Python package and a Node transform.
- **CC0 / public domain for the data.** Maximally reusable, but drops attribution
  — and a single-coder study with known limitations has a real interest in results
  staying traceable to the method that produced them.
- **A single blanket license covering `corpus/`.** Not available. MIT travels with
  the material.

## Effect on registration

None. Licensing constrains no claim and gates neither lock. Settled before L1 only
so the registration commit is unambiguous about what is being published and under
what terms.
