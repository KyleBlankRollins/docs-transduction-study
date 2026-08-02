# P3 — De-marking transform (implicit arm)

Implements **W2** — the highest-risk code in phase 1. Authority: `IMPLEMENTATION_PLAN.md` §2 W2, ADR-0002 (surgical source patching), `DESIGN.md` → The marking manipulation (D-rules, templates, propositional equivalence).

## Entry gate

- [ ] P2 exit gate re-run and passing (specimens exist).
- [ ] `grep 'spike 001: PASS' runlog.md` → the patching architecture is validated on real MDX.
- [ ] `test -f pipeline/demark/templates.json` → the template set exists as data.

## Tasks

1. **Rebuild the transform per ADR-0002.** Remark/mdast transforms for D1–D4 and D7, patching source ranges by byte offset — never re-serializing the document. Rules descend recursively; **DM-1 (nested containers) closes here as a consequence, not as a separate patch.** The prototype's rules, template loading, and vitest suite carry over; its traversal and serialization do not.
2. **Templates are the manipulation.** All inserted wording comes from `templates.json`, applied uniformly. If a specimen genuinely cannot be de-marked without a bespoke sentence, log the exception in `runlog.md` naming the specimen — per the design, frequent exceptions falsify the mechanical-manipulation claim and get *reported*, not patched over.
3. **Generate the implicit arm.** `make demark` → `corpus/implicit/`, committed. The `git diff` between arms is the reviewable record of the manipulation.
4. **Build check — exit code only.** Both arms must build clean through the pinned tree (ADR-0003). This check is pass/fail: **do not open, inspect, or retain rendered output of any study specimen** — that would put study artifacts in front of the author before L2. Output goes to the gitignored `build/` tree and is deleted after the check; runlog records the exit codes and the deletion. (The pilot page in P5 is the only page whose rendered output may be examined pre-L2.)
5. **HUMAN — propositional-equivalence review.** The analyst reads every diff hunk against the constraint that no information — including relational information — was dropped. Per-specimen sign-off entries in `runlog.md`, dated. This is manual and that is the point; an agent asserting equivalence would be the strawman threat reviewing itself.

## Hard rules

- Zero hand edits to `corpus/implicit/` — ever. The transform's output is the arm.
- The explicit arm stays byte-verbatim. Nothing in this phase touches `corpus/explicit/`.

## Exit gate

- [ ] **DM-1 closed:** `pipeline/demark/KNOWN-ISSUES.md` marks DM-1 resolved, and a vitest case covering nested containers passes in `make check`.
- [ ] **Mechanical regeneration:** delete `corpus/implicit/`, re-run `make demark`, then `git status --porcelain corpus/implicit/` → empty. Byte-identical regeneration is the proof there were no hand edits.
- [ ] **Confound absent:** for one specimen, `diff` of explicit source vs. implicit output shows changes **only** at de-marked sites — no bullet-style rewrites, no re-padded tables, no dropped blank lines (the ADR-0002 drift list).
- [ ] Build check recorded: runlog entry with both exit codes = 0 and the output-deletion note; `git ls-files build/` → empty.
- [ ] Equivalence sign-off: for every `specimen_id` in `corpus/specimens.csv`, a matching sign-off entry exists in `runlog.md`.
- [ ] Exception count logged (zero is a valid count). If exceptions > 2 specimens, flag to the maintainer before proceeding — the mechanical claim is in question and that is a reporting decision, not an engineering one.

On any failure: runlog entry, stop, report.
