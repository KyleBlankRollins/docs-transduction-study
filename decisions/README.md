# Decision records

Numbered, immutable records of decisions that shaped the study and are not
self-evident from the code or the design.

**These are not part of the registration.** `DESIGN.md` is the authority on
hypotheses, taxonomy, probes, and analysis. Where a decision recorded here also
changes the design, the design is what governs and the record says where the
change landed. A decision record explains *why*; it never overrides.

## Why keep these

The study's credibility rests on a reader being able to reconstruct what was
decided, when, and with what known at the time. Git history shows what changed;
it does not show what was rejected, or what the decision was expected to cost.
For a single-coder study that holds its own hypotheses, the rejected alternatives
are the part most worth being able to show.

The distinction that matters:

- **`AMENDMENTS.md`** — changes to registered content *after* a lock. Carries the
  question "had results been seen?" because that is what makes an amendment
  suspect.
- **`decisions/`** — reasoning behind choices, before or after a lock, registered
  or not. Carries no such question, because a decision record makes no claim.

A decision that changes registered content after a lock needs **both**: an
amendment entry and a decision record.

## Status values

| Status | Meaning |
| ------ | ------- |
| Proposed | Written up, not yet settled |
| Accepted | In force |
| Superseded by ADR-NNNN | Replaced; the record stays, unedited |
| Rejected | Considered and declined; kept so it is not re-litigated |

Records are **append-only in spirit**: correct a typo, but do not rewrite the
reasoning after the fact. Change your mind by writing the next record and marking
this one superseded.

## Format

Copy `template.md`. Keep it short — the value is in Consequences and Alternatives,
not in restating the design.

## Index

| # | Title | Status | Date |
| - | ----- | ------ | ---- |
| [0001](0001-lowercase-rfc2119-keywords.md) | De-mark RFC 2119 keywords by lowercasing them | Accepted | 2026-08-02 |
| [0002](0002-surgical-source-patching.md) | Transform by patching source ranges, not re-serializing | Accepted, pending [spike 001](../spikes/001-transform-architecture.md) | 2026-08-02 |
| [0003](0003-two-full-site-builds.md) | Produce A1 from two full builds of the pinned docs site | Accepted, pending [spike 001](../spikes/001-transform-architecture.md) | 2026-08-02 |
| [0004](0004-licensing.md) | License code MIT, study data CC BY 4.0, corpus unchanged | Accepted | 2026-08-02 |

### Decisions made before this log existed

Recorded in `IMPLEMENTATION_PLAN.md` §1 and, where they changed the design, in
`DESIGN.md`'s *What changed from 0.3* section. Not backfilled as records:

- **D-1** two-lock registration — design
- **D-4** which chunk is scored at A4 — design
- **D-5** per-arm anchors and host passages — design
- **D-2** Node for the MDX transform, Python elsewhere — engineering
- **D-3** minimal Starlight harness for A1 — **superseded by ADR-0003**

**D-8** (whether the explicit arm is round-tripped) was never settled as posed.
ADR-0002 removes the confound it was trying to balance, so the question dissolves
rather than being answered. If spike 001 fails, D-8 reopens on its original terms.
