# Phase files — execution protocol

**Status: engineering scaffolding. Not part of the registration.**

These files break `IMPLEMENTATION_PLAN.md` into discrete phases an AI agent can execute. Where a phase file and the plan disagree, the plan wins; where the plan and `DESIGN.md` disagree, the design wins and the downstream files get fixed.

## Namespaces — read this first

Four numbering systems coexist in this study. Do not conflate them:

| Prefix | Meaning | Owner |
| ------ | ------- | ----- |
| **P0–P11** | Implementation phases — these files | This directory |
| **W0–W10** | Work packages | `IMPLEMENTATION_PLAN.md` §2 |
| **A0–A5** | Pipeline stages | `DESIGN.md` → Pipeline |
| **Phase 1 / Phase 2** | The study's model-free vs. model-in-the-loop halves | `DESIGN.md` → Phasing |

P0–P10 implement the study's Phase 1. P11 is the study's Phase 2.

## Rules vs. gates

A **rule** is guidance an executor can rationalize past ("verify before asserting"). A **gate** is a blocker: the next action does not happen until an objective condition is demonstrably met. Gates in these files are written so they can only be passed with evidence in hand — a command that was actually run in this session, with its output observed. "Did I verify?" is not a gate. "Does `git cat-file -t <sha>` print `commit`?" is.

The protocol:

1. **Entry gate first.** Run every entry-gate check before any task. If one fails, stop — do the phase that satisfies it, or report. Never start tasks "in parallel with" a failing entry gate.
2. **Evidence means output you produced now.** A gate passes when its command has been run in the current session and the observable matched. Remembering that it passed before, or reasoning that it must pass, is not passing it.
3. **Gates are not editable by the executor.** If a gate seems wrong, stop and report; the maintainer changes it. Weakening a gate to pass it is the failure mode these files exist to prevent.
4. **Failures are logged, then stopped on.** Any gate failure or deviation gets a dated entry in `runlog.md` before anything else happens.
5. **HUMAN steps are hard stops.** Steps marked **HUMAN** are the analyst's, for methodological reasons stated in place. The agent prepares inputs, stops, and requests the human. Performing a HUMAN step as an agent — or synthesizing its output — invalidates the study, not just the step.

## Global hard rules

These hold in every phase and are repeated in the phases where they bind hardest:

- **No AI model answers a probe from an artifact anywhere in P0–P10.** M1a is analyst-judged and model-free; that property is the study's primary claim to durability (`DESIGN.md` → Measures). An agent that "helpfully" fills `coding/m1a.csv` has destroyed phase 1.
- **No A1–A5 artifact of a study specimen exists before the L2 commit.** The sole exception is the pilot page (P5), which is never a study specimen. This is the design's registration boundary, enforced as P7's entry gate.
- **Nothing downstream of a lock loops back silently.** After L1, design changes are amendments; after L2, instrument changes are amendments. `AMENDMENTS.md`, dated, with a results-seen flag.
- **Coding data is append-only.** No row in `coding/m1a.csv` is ever updated or deleted.
- **Every deviation lands in `runlog.md`** — the run log is the study's memory, and an unlogged deviation is the difference between a study and a story.

## Phase index and dependency graph

| Phase | Implements | Blocks on |
| ----- | ---------- | --------- |
| [P0 — Repository foundation](p00-foundation.md) | W0 | — |
| [P1 — Corpus pin, spike 001, L1 freeze](p01-spike-and-freeze.md) | W1 (pin only), spike, L1 | P0 |
| [P2 — Specimen selection](p02-specimens.md) | W1 | P1 (L1 taken) |
| [P3 — De-marking transform](p03-demark.md) | W2 | P2, spike PASS |
| [P4 — Relation inventory](p04-inventory.md) | W3 | P3 |
| [P5 — Pilot: build pipeline + harness, shake down](p05-pilot.md) | W4, and the *build* halves of W6/W7 | P3 (transform final); P4 not required |
| [P6 — Probe authoring and L2 lock](p06-probes-and-lock.md) | W5, L2 | P4, P5 |
| [P7 — Artifact generation A1–A4](p07-artifacts.md) | W6 (run) | P6 (L2 taken) |
| [P8 — M1a coding and kappa](p08-coding.md) | W7 (run) | P7 |
| [P9 — M2 redundancy inventory](p09-redundancy.md) | W8 | P4; parallel with P5–P8 |
| [P10 — Phase 1 analysis](p10-analysis.md) | W9 | P7, P8; P9 for the redundancy map |
| [P11 — Phase 2 study (deferred)](p11-phase2-study.md) | W10 | P10, and an explicit human go decision |

Sequencing note recorded here because the plan implies it without stating it: the pilot (P5) exercises the pipeline stages and coding harness end-to-end **before L2**, so that code is *built* in P5 against the pilot page and only *run* against study specimens in P7/P8. W6 and W7 in the plan describe the run; their code exists earlier.
