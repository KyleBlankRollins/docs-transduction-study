# Exploratory analysis plan for M1-AI (UNPLANNED, fixed before computation)

Status: **written 2026-11-18. Nothing in it has been computed.** The commit that adds this file fixes the plan. Any later change goes in a dated section at the end, saying what had been seen by then.

## Why this plan exists

The pre-specified M1-AI analysis (DESIGN, *Analysis plan*) and the A9 replication comparison have been run and seen. Every further analysis is therefore exploratory. This plan names those analyses, their definitions, and how they will be read **before** any of them is run. The point is that the analysis cannot drift toward an interesting cut. Anything not listed here is outside the plan and must be labelled as such.

### Already seen when this plan was written

- **Pre-specified tables, both evaluators:** H1 pooled and per specimen, H2 observed, R3 by device, H3 overall and by `spans_chunks`.
- **The A9 sign comparison.**
- **The unplanned GLM quote diagnostics and quote audit.**
- **One pattern that motivates E1.** In the GLM H2 table, the observed relations (O1, O2), which have identical wording in both arms, show arm gaps at some stages: for example, O1 at A1 is explicit 2.43 against implicit 2.55.

**Not yet computed under either evaluator:**

- any per-instance paired statistic;
- any component split beyond the pooled score distributions;
- any manipulated-versus-observed contrast;
- cross-evaluator agreement;
- stage-to-stage transitions;
- case reads of Claude answers.

## Data

- **Records:** A7-scored, first-pass records only:
  - GLM-5.3-Flash: `coding/m1_ai_a7_records/`.
  - Claude Sonnet 5.5: `coding/claude-sonnet-5-5/m1_ai_a7_records/`.

  The repeat pass is used only in the existing repeatability gate.
- **Unit of analysis:** one assignment, meaning one instance in one arm at one stage, with `assignment_id` of the form `instance|arm|stage`.
  - Instances come from the 229 retained in `instruments/instances.csv`, after removing `instruments/gate_exclusions.csv`.
  - `relation_type` and `specimen_id` come from `instances.csv`; `demark_rule` gives the marking device.
  - `spans_chunks` per arm comes from `artifacts/anchor-assignments.json`.
- **Pairs:** an *instance-stage pair* is the explicit and implicit assignment for one instance at one stage.
  - Paired statistics use complete pairs only. A pair is incomplete when an assignment is documented unscorable (5 per evaluator).
  - Incomplete pairs are counted and listed, never imputed.
- **Groups:**
  - *Manipulated* means R1–R4 (123 instances: R1 31, R2 34, R3 49, all D3, R4 9).
  - *Observed* means O1–O2 (106 instances: O1 54, O2 52).
- **Evaluators:** always analyzed separately. Results are never pooled across evaluators.

## Outcome definitions

From the 0–3 A7 score of each assignment:

| Outcome | Definition | Reading |
| ------- | ---------- | ------- |
| `correct` | score ≥ 2 | the relation was recovered |
| `quotable` | score = 3, among correct answers | the recovered relation was backed by a verified explicit quote |
| `absent` | score = 1 | the evaluator chose "The text does not say" (visible loss) |
| `corrupted` | score = 0 | the evaluator chose a foil (silent loss) |
| `score` | 0–3 | the composite used by the pre-specified tables |

`quotable` is reported two ways:

- **Conditional:** among pairs where both arms are `correct`. This removes differences in which instances were answered correctly.
- **Unconditional:** among all correct answers in each arm.

## Common statistics (apply to every analysis)

- **Gaps** are explicit minus implicit, computed within each complete pair, then averaged. A negative gap favours the implicit arm.
- **Uncertainty** is a page-clustered bootstrap:
  - Resample the 12 specimens with replacement, keeping all of each specimen's instances.
  - Use 10,000 resamples and report 95% percentile intervals.
  - Seed the random generator from the SHA-256 of the string `exploratory-plan-2026-11-18`.
- **Consistency:** for each gap, the number of the 12 specimens whose own gap is negative, zero, or positive.
- **No p-values as results.** Intervals and specimen consistency are descriptive. With 12 pages they support description, not inference to documentation in general.
- **Full counts:** every table reports n and raw counts alongside rates and means.

## Analyses

### E1 — Manipulated versus observed relations (difference in differences)

For each evaluator and stage:

- `G_R`: mean paired gap over manipulated instances.
- `G_O`: mean paired gap over observed instances.
- `DiD = G_R − G_O`: the part of the arm gap specific to the relations whose marking was changed.

Computed for `score`, `correct`, `quotable` (both versions), `absent`, and `corrupted`. Intervals for `DiD` resample specimens jointly for both groups.

### E2 — What the composite score is made of

For each evaluator × stage × arm:

- rates of `correct`, `quotable`, `absent`, and `corrupted`, with their paired gaps;
- a decomposition of the composite `score` gap into the parts carried by each score boundary: 0 versus 1, 1 versus 2, and 2 versus 3.

### E3 — Specimen-level picture

For each evaluator × stage: each specimen's paired `score` and `correct` gaps, plotted as 12 points per stage, with the specimen consistency counts. This shows whether any pooled gap is broad or comes from a few pages.

### E4 — Agreement between evaluators

On first-pass assignments scored by both evaluators:

- unweighted Cohen's kappa on the 0–3 score and on `correct`;
- the 4 × 4 confusion table;
- agreement split by stage and arm.

Then each of the E1 and E2 gaps is recomputed on the assignments where the two evaluators gave the same score. That shows how much of each gap depends on assignments where they disagree.

### E5 — Trajectories within instances

For each evaluator and arm:

- **Transitions:** counts of moves between score categories from A1 to A2, A2 to A3, and A3 to A4.
- **First stage of loss:** the first stage at which an instance scores below 3, and the first stage at which it scores 1 or below, with "never" as a category.
- **Widening within an instance:** the distribution of each instance's change in paired gap from A1 to A4. This tests H1's "the gap widens" claim within instances rather than on pooled means.

### E6 — By relation type and chunk boundary

E1 and E2 quantities by relation type (R1, R2, R3, R4, O1, O2) and stage, with n.

- R4 (9 instances) is reported but marked as too small to interpret.
- R3 is entirely D3 (admonitions); no D4 instances exist.
- At A4, `absent` and `corrupted` are also split by each arm's `spans_chunks`.

### E7 — Case reading

Cases:

- every `corrupted` assignment under either evaluator;
- a seeded random sample of 20 `absent` assignments at A4 per evaluator, drawn with the bootstrap seed and purpose string `absent-sample`.

For each case, read the artifact, the probe, the options, and the answer, and assign exactly one category. The categories are fixed now:

- **(a) Evidence missing:** the evidence for the relation is not in the artifact (lost in extraction or cut at a chunk boundary).
- **(b) Structure lost:** the evidence is present, but the structure carrying the relation was lost or changed into another relation (for example, tabs read as a sequence).
- **(c) Misread:** the evidence and structure are present, and the evaluator misread them.
- **(d) Ambiguous:** the probe or its options are ambiguous for this artifact.

Coding is AI-assisted and labelled as such. The maintainer reviews every category assignment, and any change is recorded with its reason.

## How results will be read (fixed now)

- **Robust:** a gap is called robust only if it has the same sign under both evaluators **and** in at least 8 of the 12 specimens under each evaluator. Anything else is reported as mixed.
- **Marking effect:** if `DiD` for `score` is near zero with an interval covering zero, while `G_R` and `G_O` are both negative, the implicit advantage is attributed to the de-marked page or the evaluator's response to it, not to marking the relation. If `DiD` is robustly negative, prose carried the manipulated relations better than markup, beyond any page-level effect.
- **Quotability versus recovery:** if the gap shows in `quotable` but not in `correct`, it is reported as a difference in how quotable the support is, not in whether the relation survived. The rubric's reward for quotable statements will be discussed as a measurement issue.
- **H1 within instances:** H1-style widening is claimed only if each instance's change in paired gap from A1 to A4 (gap at A4 minus gap at A1) is positive, meaning the explicit arm gains ground down the pipeline, and that holds robustly by the rule above. Otherwise H1 remains unsupported.
- **Case reading** illustrates and checks the numbers. It does not add new quantitative claims.

## Not done

- Pooling evaluators.
- Headline p-values or significance tests that treat assignments as independent.
- Subgroups not named above.
- Re-scoring under different rules, or changing A7, A8, or A10.
- Using the repeat pass beyond the existing gate.
- Ordinal mixed models (fragile with 12 clusters).

## Outputs

- **Code:** one script (`exploratory.py` extended, or a new module), with unit tests on synthetic records before it reads study data.
- **Location:** outputs under `analysis/exploratory/plan-2026-11/`, one subfolder per evaluator plus a combined comparison.
- **Labelling:** a README states "UNPLANNED exploratory; plan fixed at commit <SHA> before computation".
- **Runlog:** an entry when the analysis is run.

## Changes after this commit

(None yet.)
