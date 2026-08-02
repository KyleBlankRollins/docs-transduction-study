# P11 — Phase 2 study (deferred)

Implements **W10** — the study's Phase 2: A5 generation, M1b, the closed-book covariate, H4. Authority: `IMPLEMENTATION_PLAN.md` §2 W10; `DESIGN.md` → Measures (M1b), Contamination, Implementation note: Inspect AI.

**This phase is deliberately a stub.** It is not started by an agent on its own initiative, and it is not elaborated until its entry gate is within reach — the design's phasing exists so that phase 1 stands alone if this phase never runs.

## Entry gate

- [ ] P10 exit gate passing, **on the "κ ≥ 0.6" branch** — a failed instrument is not carried into model runs.
- [ ] **HUMAN — explicit go decision**, recorded in `runlog.md`. Phase 2 spends money on model calls and dates the results; whether and when is the maintainer's call, not a dependency edge.
- [ ] Inspect AI's current API verified against its documentation (not memory); version pinned in `uv.lock` and recorded alongside intended model IDs.

## Scope, when opened

- Inspect tasks for **A5 generation** (fixed prompt, ≥3 models, ≥2 vendors) and **M1b** (forced-choice, exact-match scoring against the locked answer key — no judge model anywhere).
- **M1b and the closed-book covariate as two tasks over one shared dataset definition**, so a probe amendment propagates to both or neither.
- Epoch reducer declared in `runlog.md` **before** the first run.
- Version-change probes carry H4; closed-book covariate collected (one extra call per probe).
- Eval logs published to `logs/`; model IDs, versions, temperature, dates recorded.
- M1b results reported per specimen-age stratum with the training-data familiarity confound named, per the design's Contamination section; only the H1-divergence replication is claimed as durable.

## Hard rules

- The locked instrument is not touched. A phase-2 need that seems to require a probe change is an amendment conversation, not an edit.
- Model outputs never flow back into `coding/m1a.csv` or any phase-1 artifact.

## Exit gate

To be written when the phase is opened, with the maintainer, before the first model call — and committed before any result exists.
