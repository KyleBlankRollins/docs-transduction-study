# P1 — Corpus pin, spike 001, L1 freeze

Implements the **pre-L1 slice of W1** (the pin), **spike 001**, and **L1**. Authority: `IMPLEMENTATION_PLAN.md` §7 (ordering and rationale), `spikes/001-transform-architecture.md`, `DESIGN.md` → Status (what L1 freezes). The spike sits before L1 deliberately: a spike failure must cost an edit to an unfrozen design, not a retaken registration.

## Entry gate

- [ ] Every P0 exit-gate check re-run and passing.
- [ ] `test -f spikes/001-transform-architecture.md` → the spike has a written brief before it is run.

## Tasks

1. **Pin the corpus.** `git submodule add https://github.com/withastro/docs vendor/astro-docs`, then check out the chosen SHA inside the submodule and commit. Runlog entry: the SHA and the date pinned. Submodule, not clone — the SHA becomes an object in this repo's history.
2. **Pull engineering fixtures.** Copy 3–5 component-dense pages from `vendor/astro-docs/src/content/docs/en/` into the spike's workspace. These are parsing fixtures chosen for `<Steps>`/`<Tabs>`/aside/table density. **This is not specimen selection** — selection is gated on L1 (P2) and these pages carry no standing there. They are deleted when the spike ends.
3. **Run spike 001** per its brief: does byte-offset source patching (ADR-0002) hold on real nested Astro MDX? Timebox two days. Record findings in `runlog.md` as the spike brief requires.
4. **Record the verdict.** One runlog line: `spike 001: PASS` or `spike 001: FAIL`, dated, with a pointer to the findings.
   - **On FAIL — hard stop.** D-8 reopens on its original terms with a design edit attached (`IMPLEMENTATION_PLAN.md` §7). That edit is the maintainer's decision. Log it, report, do nothing further in any phase.
5. **HUMAN — take L1.** Freezing the design is the registrant's act, not the agent's. Present the maintainer with: spike verdict, `DESIGN.md` at v0.5, confirmation that P0's exit gate passes. On their go:
   - Commit the freeze (a commit whose message names L1).
   - A commit cannot contain its own SHA: take the freeze commit's SHA, write it into `DESIGN.md` frontmatter (`registered: <date>`, `registration_commit: <sha>`) in an immediately following commit, and mirror both in `runlog.md`. This two-commit convention *is* the registration; note it in the runlog entry.

## Hard rules

- Fixture pages never appear in `corpus/` and never inform specimen selection.
- No task from P2 onward starts before the L1 fields exist. After L1, changes to hypotheses, taxonomy, rubric, de-marking rules, pipeline definitions, or the analysis plan are amendments.

## Exit gate

- [ ] `git submodule status vendor/astro-docs` → prints a SHA (not a branch ref); same SHA appears in `runlog.md`.
- [ ] `grep 'spike 001: PASS' runlog.md` → present. (On FAIL this phase does not exit.)
- [ ] Spike fixtures deleted: `git status --porcelain spikes/` clean, no fixture files tracked outside the spike's findings notes.
- [ ] `grep -E 'registered: "?[0-9]{4}' DESIGN.md` and `grep -E 'registration_commit: "?[0-9a-f]{7,}' DESIGN.md` → both fields non-empty.
- [ ] `git cat-file -t <registration_commit value>` → prints `commit`.
- [ ] `runlog.md` contains the L1 entry: date, SHA, and who took the freeze decision.

On any failure: runlog entry, stop, report.
