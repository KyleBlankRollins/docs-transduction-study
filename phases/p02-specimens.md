# P2 — Specimen selection

Implements **W1** (post-pin). Authority: `IMPLEMENTATION_PLAN.md` §2 W1, §3 (`specimens.csv` contract); `DESIGN.md` → Corpus (selection rules, targets).

## Entry gate

- [ ] L1 is taken: `registered` and `registration_commit` non-empty in `DESIGN.md`, and `git cat-file -t <registration_commit>` → `commit`. Selection before L1 is the exact ambiguity the two-lock model exists to prevent.
- [ ] `git submodule status vendor/astro-docs` → pinned SHA present.

## Tasks

1. **Build the selection evidence.** Implement `corpus.py` / `make corpus-report`: enumerate candidates under `vendor/astro-docs/src/content/docs/en/`, emit per-page counts of `<Steps>`, `<Tabs>`, asides, tables, and normative keywords. Commit the report. Selection must be informed by where the manipulated relations actually live.
2. **HUMAN — select specimens.** Selection is the analyst's judgment call and one of the single-coder limitations the design discloses; an agent choosing specimens adds an undisclosed selector to a registered protocol. Present the component-count report and the design's rules (span Diátaxis types; record last-major-change version; 8–12 specimens; instance targets ≥20 per type). The human fills every row of `corpus/specimens.csv` including `selection_rationale` — the rationale is the artifact that makes selection inspectable, and it is not the agent's to write.
3. **Copy specimens verbatim** to `corpus/explicit/`, preserving relative paths.
4. **Runlog entry:** selection date, count, Diátaxis coverage, and any anticipated cell-minimum risk.

## Hard rules

- The pilot page (P5) is **never** one of these specimens. Selection here defines the set the pilot must avoid.
- `selection_rationale` is human-authored text. Do not generate, summarize, or "improve" it.

## Exit gate

- [ ] `corpus/specimens.csv` row count (minus header) → between 8 and 12.
- [ ] No empty cells: every row has `specimen_id`, `source_path`, `diataxis_type`, `last_major_change_version`, `selection_rationale`.
- [ ] Diátaxis coverage: ≥3 distinct `diataxis_type` values, or a runlog entry recording why not.
- [ ] Verbatim copies: for every `source_path`, `diff vendor/astro-docs/<source_path> corpus/explicit/<source_path>` → no output.
- [ ] Component-count report committed: `git ls-files | grep <report path>` → present.

On any failure: runlog entry, stop, report.
