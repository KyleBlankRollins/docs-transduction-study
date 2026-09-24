# P6 — Probe authoring and the L2 lock

Implements **W5** and **L2**. Authority: `IMPLEMENTATION_PLAN.md` §2 W5/L2, §3 (`probes.csv`, `gate_exclusions.csv`); `DESIGN.md` → Probes (authoring rules, foil cap, the both-arms gate), Status (what L2 freezes).

**Current execution (2026-09-23):** [amendment A3](../DESIGN.md#ai-assisted-execution-amendment-a3) authorizes AI authoring and gating; the historical HUMAN assignments below no longer reserve those tasks. All 567 occurrence candidates are reviewed and migrated (106 accepted); 242 instances carry per-arm hosts, anchors, and verbatim gate evidence; 229 probes plus 13 dated exclusions pass `make lint-probes`, and `make anchors-a0` verifies unique both-arm A0 resolution. Three version-change probes have verified superseded sources. The gate was run by the authoring assistant (not independent). The AI evaluator protocol was frozen after the approved live smoke test, and **L2 was taken on 2026-09-23 at commit `ace31884`** (see runlog). Historical checkmarks below do not override these facts.

## Entry gate

- [ ] P4 exit gate passing (inventory complete, A0 anchors resolve).
- [ ] P5 exit gate passing (pilot disposed of — no pilot material can leak into probe authoring).

## Tasks

1. **Build the probe linter** (`make lint-probes`), enforcing by code what memory would rationalize: exactly one probe per instance (full join against `instances.csv`); no probe string appears verbatim in either arm's A0 source; ≤2 foils; foils are _relations_, not paraphrases of absence; `version_change=true` rows have non-empty `superseded_answer` **and** `superseded_source`.
2. **HUMAN — author the probes.** Probe writing is the instrument. The analyst writes question, correct answer, and foils for every instance, per the design's authoring rules. The agent may surface the instance list and host passages; it does not draft, suggest, or complete probe text.
3. **HUMAN — the both-arms gate.** The analyst answers every probe from both A0 variants, artifact only. Failures are excluded into `instruments/gate_exclusions.csv` with reasons — before the lock, or they are not exclusions.
4. **Version-change subset.** Designated against specimen change-versions; every `superseded_answer` verified against a pre-change source (docs tree at a pre-change SHA, or the changelog entry), recorded in `superseded_source`. An unverified superseded answer is not a version-change probe.
5. **Generate the coding-order seed** and commit it (`coding/seed`).
6. **HUMAN — take L2.** The registrant's act, as at L1. On their go: commit `specimens.csv`, `instances.csv`, `probes.csv`, `gate_exclusions.csv`, `templates.json`, and the seed in a commit whose message names L2; then write the SHA into `DESIGN.md` frontmatter (`instrument_locked`, `instrument_lock_commit`) in the following commit, mirrored in `runlog.md` (the same two-commit convention as L1).

## Hard rules

- **No A1–A5 artifact of any study specimen exists yet.** If one does, this phase has already failed — stop and report before locking anything.
- After L2, every instrument change is an amendment. The lock is the point of this phase, not its paperwork.

## Exit gate

- [ ] `make lint-probes` → exits 0 on the locked `probes.csv`.
- [ ] Probe count == instance count minus exclusion count (script-checkable equality).
- [ ] `instruments/gate_exclusions.csv` exists (empty is valid) and every row has a reason and date.
- [ ] `grep -E 'instrument_locked: "?[0-9]{4}' DESIGN.md` and `grep -E 'instrument_lock_commit: "?[0-9a-f]{7,}' DESIGN.md` → both non-empty; `git cat-file -t <instrument_lock_commit>` → `commit`.
- [ ] `git show --name-only <instrument_lock_commit>` → lists all six instrument files.
- [ ] Runlog L2 entry: date, SHA, decision-taker.

On any failure: runlog entry, stop, report.
