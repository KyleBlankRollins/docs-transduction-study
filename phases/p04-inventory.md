# P4 — Relation inventory

Implements **W3**. Authority: `IMPLEMENTATION_PLAN.md` §2 W3, §3 (`instances.csv` contract); `DESIGN.md` → Relation taxonomy (R1–R4, O1–O2, anchors, host passages) and Corpus (cell minimums).

## Entry gate

- [ ] P3 exit gate re-run and passing — both arms exist and the implicit arm regenerates byte-identically.

## Tasks

1. **Automatic R1–R4 candidates.** Walk the explicit arm's component tree: a `<Steps>` block *is* an R1 instance; tabs → R2, **including the corpus's custom tab wrappers** (`PackageManagerTabs` and family — see runlog 2026-08-02), not only raw `<Tabs>`; admonitions and normative keywords → R3 (tag which — D3 vs D4 matters to the analysis split); prerequisite blocks and tables → R4. Emit candidates with `demark_rule` populated. **Anchor rule for wrapped tabs:** anchors come from panel content (command text), never tab labels — the labels live in the component and do not exist in A0 source.
2. **O1/O2 candidates by assist script.** Surface candidate referring expressions (O1) and deictic expressions (O2) from both arms' shared text. Candidates only — the script proposes, it never classifies.
3. **HUMAN — classify O1/O2 and confirm R1–R4.** Instance classification defines the unit of analysis; it is analyst judgment inside a locked-at-L2 instrument. The human accepts/rejects candidates and resolves boundaries.
4. **Anchors and host passages, per arm.** For every accepted instance, record `anchor_explicit`/`anchor_implicit` (short verbatim substrings of that arm's A0 source) and both host passages. Populate `instruments/instances.csv` per the §3 contract.
5. **A0 resolution.** Implement `make anchors-a0`: every anchor must be found in its arm's A0 source, using the committed normalization spec. Fix defective anchors now — this is pre-L2 and free.
6. **Cell counts.** Implement `make inventory-counts`: instances per type (R1, R2, R3-D3, R3-D4, R4, O1, O2). If any cell < 20, that is discovered **now**: either the human widens selection (legitimate pre-L2; rerun P2's exit gate and the affected P3 steps for added specimens) or the shortfall is recorded in `runlog.md` before anything runs — the design requires the recording, not the reaching.

## Hard rules

- Anchors never appear in probes and are never shown to the coder (design → Relation taxonomy). They are location machinery only.
- An instance the human did not confirm does not enter `instances.csv`.

## Exit gate

- [ ] `instruments/instances.csv` complete: no empty required cells; every `relation_type` ∈ {R1, R2, R3, R4, O1, O2}; `demark_rule` populated for R-instances, blank for O-instances.
- [ ] `make anchors-a0` → exits 0: 100% of anchors resolve in both arms at A0.
- [ ] `make inventory-counts` → report committed; every cell ≥ 20 **or** a dated shortfall entry exists in `runlog.md`.
- [ ] Every `specimen_id` in `instances.csv` exists in `corpus/specimens.csv` (referential integrity, checkable by script).

On any failure: runlog entry, stop, report.
