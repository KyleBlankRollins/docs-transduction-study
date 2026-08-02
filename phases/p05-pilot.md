# P5 — Pilot: build the pipeline and harness, shake down end-to-end

Implements **W4**, plus the **build halves of W6 and W7** — the pilot cannot run A1→A4 and a coding dry run unless the stage drivers and coding harness exist, so they are built here and merely *run* in P7/P8. Authority: `IMPLEMENTATION_PLAN.md` §2 W4/W6/W7, ADR-0003; `DESIGN.md` → Status (pilot carve-out), Pipeline (A2 policy, A3 extractor, A4 chunker, normalization spec).

## Entry gate

- [ ] P3 exit gate passing (the transform is final — piloting against a prototype tests nothing).
- [ ] **Pilot page selected and clean:** the chosen page's path does **not** appear in `corpus/specimens.csv` (`grep` → no match). Record the page and the selection date in `runlog.md`. This is the v0.5 carve-out's condition: the author sees no study specimen's downstream artifacts before L2.

## Tasks

1. **Build the stage drivers** (`src/docs_transduction_study/stages/`), per the W6 table:
   - **A1** — two full `astro build` runs of the pinned tree (explicit / implicit), ADR-0003. Record Node version, package manager, and determinism check (two builds, same input → compare).
   - **A2** — Playwright accessibility snapshot of the served page, **default page state, no interaction** (registered policy). Expect inactive tab panels to be absent, not flattened; that is a finding about A2, record its shape.
   - **A3** — named, versioned extractor in plain-text mode, article element only; config recorded.
   - **A4** — fixed-size, no-overlap, **character-based** chunker; parameters recorded; size justified in `runlog.md`.
2. **Build `anchors.py`:** locate instances in artifacts through the committed normalization spec; emit A4 chunk assignment (chunk containing the first character of the host passage) plus `spans_chunks`.
3. **Build the coding harness** (`coding.py`), two entry points per W7: `setup` (shuffle by seed, opaque IDs, manifest, mapping encrypted at rest) and `code` (presents artifact + probe + randomized options; captures choice and explicit/inferred flag; **its read path contains no mapping**; requires an interactive TTY and refuses piped input — a structural barrier against automated coding). Append-only `m1a.csv` writes, enforced in code and unit-tested.
4. **Write three disposable pilot probes** for the pilot page. They may be authored freely — they are destroyed with the pilot.
5. **Run the pilot:** pilot page through A1→A4, anchor resolution, `setup`, and a one-hour human coding dry run (**HUMAN** — the dry run is also testing the human's tooling). Log findings: build determinism, a11y-tree shape for tabs, chunk sanity, theme-chrome bleed into A3/A4, harness usability.
6. **Dispose on the record.** Delete pilot artifacts and probes; `runlog.md` entry with the date, per the carve-out.

## Hard rules

- Only the pilot page's artifacts may be examined in this phase. If a stage driver accidentally processes a study specimen, delete the output unexamined and log the event.
- Pilot probes are never reused, adapted, or "referenced" when authoring real probes in P6.

## Exit gate

- [ ] End-to-end completed: runlog findings entry covers A1 determinism, A2 tab shape, A3 extraction quality, A4 chunk sanity, and harness usability.
- [ ] `make check` → green: stage drivers, anchors, and harness have tests, including the append-only and TTY-refusal behaviors.
- [ ] **Disposal proven:** no pilot artifacts remain (`git ls-files artifacts/` → empty; working tree clean of pilot output); pilot probes absent from `instruments/`; dated disposal entry in `runlog.md`.
- [ ] Any surprise that changes a registered definition (e.g., the A2 policy produces nothing usable) → **stop**: that is a pre-L2 design edit for the maintainer, not a workaround.

On any failure: runlog entry, stop, report.
