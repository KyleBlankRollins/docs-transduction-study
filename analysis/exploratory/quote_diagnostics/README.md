# Quote diagnostics

UNPLANNED exploratory analysis (not pre-specified), run 2026-09-27 after the pre-specified M1-AI results were seen. Model-conditioned; A7 scoring.

UNPLANNED exploratory diagnostics for M1-AI (not pre-specified; see DESIGN).

Requested by the maintainer on 2026-09-27 after the pre-specified results were
seen, to test whether the implicit arm's higher scores reflect quote
verifiability rather than survival of the relation. Outputs go only under
``analysis/exploratory/`` and never replace the pre-specified tables.

1. ``correctness_by_stage_arm.csv``: right answer (score 2 or 3) versus not
   (0 or 1), with the explicit-minus-implicit gap per stage.
2. ``support_breakdown_by_stage_arm.csv``: how correct answers were supported:
   exact quote, quote verified only after A7 normalization, explicit quote
   that could not be verified, or support the evaluator itself marked inferred.

