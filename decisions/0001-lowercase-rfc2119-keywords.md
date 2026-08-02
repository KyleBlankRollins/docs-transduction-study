# ADR-0001 — De-mark RFC 2119 keywords by lowercasing them

- **Status:** Accepted
- **Date:** 2026-08-02
- **Relates to:** `DESIGN.md` → *The marking manipulation*, rule D4; `IMPLEMENTATION_PLAN.md` → D-7; `pipeline/demark/templates.json` → `d4_force_keywords`

## Context

Rule D4 de-marks illocutionary force carried by RFC 2119 normative keywords. The
design states it as *"Normative keywords → ordinary modals,"* with `MUST` →
"needs to" as the illustrative mapping.

Building the transform showed the illustration does not survive mechanical
application. The corpus's most common construction is second-person imperative
guidance, and the substitution breaks agreement:

> You **MUST** restart the server. → You **needs to** restart the server.

A template cannot fix subject–verb agreement, and a mechanical transform has no
parse to fix it from. Hand-correcting per specimen is precisely what the frozen
template set exists to prevent.

The damage is not cosmetic. Ungrammatical text would appear in the **implicit arm
only**. That makes the two arms distinguishable on fluency rather than on marking
— a confound in the treatment itself, visible to any human coder at M1a and to
any model at M1b, and running in the same direction as the hypothesis.

## Decision

D4 de-marks by **lowercasing the keyword** and nothing else: `MUST` → `must`,
`MUST NOT` → `must not`, `SHOULD` → `should`, and so on for the full RFC 2119 set.
Matching stays case-sensitive and whole-word.

The mapping lives in `pipeline/demark/templates.json` under `d4_force_keywords`
and is frozen at L2 with the rest of the template set.

The justification is not merely that it is grammatical. **RFC 8174 is the source
the series' own worked example rests on**: a keyword carries normative weight
*only* in all capitals, and a lowercase `must` is ordinary English carrying the
same force. Capitalization *is* the marking. Removing it is therefore the
de-marking — exactly, minimally, and with nothing else disturbed. The design's own
wording, "normative keywords → ordinary modals," is satisfied; the parenthetical
was an illustration, not a specification.

## Consequences

**D4 becomes the smallest manipulation in the set** — one character class, where
D1, D2, and D3 restructure blocks. Two things follow, and both are costs:

1. **D4 may contribute little or nothing to the H1 trajectory.** Capitalization
   survives every deterministic stage — HTML, accessibility tree, plain text,
   chunking — intact. If D4 instances show a gap at all, it will be at A5 or in
   M1b, where an interpreter's sensitivity to case is what is being measured, not
   the pipeline's preservation of it. A flat D4 trajectory is the expected result,
   not a surprising one.
2. **D4 instances must be reported separately, not pooled into the R3 total.**
   R3 (Force) is carried by both admonitions (D3) and keywords (D4). Pooling a
   block-level restructuring with a case change would let D3's effect masquerade
   as a property of "force marking" in general. The analysis plan's per-type
   reporting needs this split, and it should be stated before results are seen —
   which is now.

The benefit is that the manipulation is clean. Propositional content, sentence
structure, word choice, and register are all identical between arms at a D4 site.
The only difference is the one the design claims to be testing. No other rule in
the set achieves that, and it makes D4 the best available evidence that a measured
gap is attributable to marking rather than to prose quality.

There is also a smaller, real gain: the RFC 2119/8174 example is part 1's worked
example in the surrounding series. Implementing D4 as literally RFC 8174's own
distinction keeps the experiment and the essay describing the same object.

### What to watch

- **D4 hit counts at M1/M3.** If Astro's docs use few or no all-caps normative
  keywords, D4 contributes almost no instances and the R3 cell may not reach the
  design's ≥20 minimum on D3 sites alone. Discovered at M3, before L2, when
  widening specimen selection is still free.
- **A flat D4 trajectory being read as evidence against H1.** It is not. It is
  evidence about one narrow marking device that the deterministic pipeline happens
  to preserve. Publication must not let a null on D4 dilute a result on D1–D3.
- **Case-insensitive downstream tooling.** If the A3 extractor or the chunker
  normalizes case anywhere, D4 collapses to a no-op and both arms become
  identical at those sites. Check during the M4 pilot; if it happens, D4 instances
  are unusable from that stage onward and must be reported as such.

## Alternatives rejected

- **The design's `MUST` → "needs to" mapping.** Ungrammatical under mechanical
  application, in the implicit arm only. Rejected as a confound.
- **A grammatically-aware paraphrase** ("MUST" → "must" / "needs to" / "is
  required to" depending on subject). Requires a parse and a judgment call per
  site, which is hand-tuning with extra steps — the exact failure mode the frozen
  template set exists to prevent, and the High-rated strawman threat.
- **Deleting the keyword entirely.** Removes force rather than re-encoding it.
  Violates propositional equivalence by construction, and would guarantee an H1
  result that measures the transform rather than the pipeline.
- **Dropping D4 and testing force only through D3 admonitions.** Loses the
  cleanest manipulation in the set, and abandons the RFC 2119 case that motivates
  the series' argument. If D4 proves unusable after the M4 pilot, this becomes the
  fallback — as a logged deviation, not a silent one.

## Effect on registration

**Gates L1.** The design's D4 row is edited to match before the design freeze, so
the frozen document and the frozen template set agree. No amendment is required —
this lands before any lock.

The commitment to report D4 separately from D3 within R3 is a pre-specification,
made before any artifact exists, and belongs in the analysis plan rather than
only here.
