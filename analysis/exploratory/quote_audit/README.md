# Quote audit (UNPLANNED, exploratory)

UNPLANNED blinded audit of unverifiable M1-AI quotes (exploratory).

Requested by the maintainer on 2026-09-27 after the pre-specified results were
seen. A seed-selected sample of first-pass answers flagged
``explicit_quote_unverified`` (equal numbers per arm, stratified by stage) is
judged by an isolated AI auditor from a different model family than the
evaluator. Each audit packet contains only an opaque item ID, the quote, and
the artifact's readable text; arm, stage, instance, and scores are withheld
(blinding is partial: page text can reveal the arm, e.g. tab labels versus
"If you are using npm:" sentences). The item-to-assignment key is stored
separately and joined only for the summary.

