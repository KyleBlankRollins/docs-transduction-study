# P10 — Phase 1 analysis

Implements **W9**. Authority: `IMPLEMENTATION_PLAN.md` §2 W9; `DESIGN.md` → Analysis plan (pre-specified outputs), Disconfirming outcomes, Limitations.

**Current execution (2026-09-23):** `analysis.py` (`make kappa`, `make analyze`) implements the pre-specified M1-AI tables against synthetic data, gated on coverage, isolation, one configuration, and kappa >= 0.6. Outputs are exploratory and model-conditioned; the trajectory figure is not yet generated. No real records exist.

## Entry gate

- [ ] P7 and P8 exit gates re-run and passing.
- [ ] P9 exit gate passing, or the redundancy map explicitly deferred in `runlog.md` (it feeds part 2, not H1–H3).
- [ ] The kappa branch is on the record (P8). **If the branch is "κ < 0.6":** the only deliverable this phase produces is the instrument-failure report — skip tasks 2–4, produce task 5's report describing the failure, and publish the dataset and process. No findings.

## Tasks

1. **Logged decryption.** Decrypt the artifact mapping; record the decryption date in `runlog.md`. This is the single sanctioned unsealing.
2. **Pre-specified outputs only**, per the design's analysis plan, each as committed script + figure/table:
   - Survival by arm × stage, pooled **and per specimen**; trajectory figure, both arms overlaid; per-stage gap (H1).
   - Survival by observed type × stage; fragility ranking with its descriptive caveat (H2).
   - Corrupted : Absent ratio at A4, overall and split by `spans_chunks` (H3).
   - R3 split by marking device (D3 vs D4), never pooled.
   - Redundancy map (M2), if P9 delivered.
   - Raw counts and full distributions throughout; effect sizes lead; no p-value-led reporting.
3. **Exploratory separation is structural.** Anything not listed above is emitted only under `analysis/exploratory/` — the directory boundary is the label, so labeling cannot depend on memory.
4. **Reconciliation:** every figure traces to `m1a.csv` rows by script; numbers in tables are generated, never hand-typed.
5. **Publishability check:** dataset, scripts, `runlog.md`, and `AMENDMENTS.md` are complete and consistent; `make check` green; a fresh-clone run of `make analyze` reproduces the figures byte-for-byte or with documented nondeterminism.

## Hard rules

- No new subgroup, no new cut, no "quick look" outside the pre-specified list lands anywhere except `analysis/exploratory/`.
- Disconfirming outcomes are written up with the same care as confirming ones — the design commits to publishing them, and the runlog shows which branch was taken **before** results were seen.

## Exit gate

- [ ] Every pre-specified output exists as a committed script + artifact pair; `figures/` contains nothing outside the pre-specified list.
- [ ] `analysis/exploratory/` is the only home of anything unlisted (`git ls-files figures/ analysis/` audit).
- [ ] Decryption date logged; mapping handling consistent with P7's seal record.
- [ ] Fresh-clone `make analyze` reproduces the outputs (or runlog documents the nondeterminism and its source).
- [ ] Runlog closes phase 1: dated entry stating the H1/H2/H3 outcomes in one sentence each, including nulls, and that part 3 is draftable.

On any failure: runlog entry, stop, report.
