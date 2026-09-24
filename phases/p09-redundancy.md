# P9 — M2 redundancy inventory

Implements **W8**. Authority: `IMPLEMENTATION_PLAN.md` §2 W8, §3 (`m2_redundancy.csv`); `DESIGN.md` → Measures (M2). Runs **in parallel** with P5–P8 any time after P4 — an ordering the design (v0.5) explicitly permits, because this measure reads no pipeline artifacts and touches nothing either lock freezes.

**Current execution (2026-09-23):** `make m2` captures pinned Astro 7.0.2 CLI/runtime observations in disposable sandboxes and writes an AI-assisted `coding/m2_redundancy.csv` (242 rows). Only eight rows carry capture-backed CLI/runtime judgments; the rest are `unobserved`, not absent. Human judgment tasks below are superseded by A3 only in that the inventory is labeled AI-assisted.

## Entry gate

- [ ] P4 exit gate passing (`instances.csv` is the row source).
- [ ] A working Astro CLI sandbox: a scratch project where `astro --help`, builds, and error output can be observed. This is the only part of phase 1 that touches the product; keep it outside the study repo's data directories.

## Tasks

1. **Scaffold** `coding/m2_redundancy.csv` — one row per relation instance, channels as booleans, `evidence_note` per row.
2. **Gather channel evidence mechanically** where it is mechanical: capture `astro --help` output, flag names, and error strings; trigger representative builds and record outcomes. Raw captures may be collected by the agent — they are observations of the product, not judgments.
3. **HUMAN — judge channel carriage.** Whether a channel *carries* a given relation is analyst judgment against the design's definitions (metalinguistic / static / dynamic). The human sets the booleans and writes `evidence_note`; the agent may present its captures alongside each instance.
4. **Emit the redundancy map** (channels per relation, by type) as a committed table for P10.

## Hard rules

- Do not run product commands inside `corpus/`, `artifacts/`, or `vendor/` — the sandbox is disposable and separate.
- `evidence_note` cites observed output, not inference about what the CLI "probably" does.

## Exit gate

- [ ] Every `instance_id` from `instances.csv` has a row; all three channel booleans set; no empty `evidence_note`.
- [ ] Redundancy map committed; counts reconcile with the CSV by script.
- [ ] Runlog entry: Astro CLI version observed, sandbox disposal date.

On any failure: runlog entry, stop, report.
