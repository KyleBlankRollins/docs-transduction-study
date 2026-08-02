# Implementation Plan

**Status: working document. Not part of the registration.**

`DESIGN.md` (once copied in) is the source of truth for hypotheses, taxonomy, probes, and analysis. This file is engineering scaffolding: what code has to exist, in what order, with what data contracts, so the procedure in the design can actually be executed. It may be edited freely at any time — including after registration — because nothing in it constrains a result. Where this plan and the design disagree, the design wins and this file gets fixed.

Source of truth at time of writing: `syntax-of-documentation.experiment-semiotics.md`, **design version 0.5**, in the Web-Portfolio repo under `source/site/content/__drafts/`.

---

## 1. Decisions

Eight choices that change the shape of the repository. **All are now settled** — four resolved into the design, one as an engineering decision, two superseded by decision records, and one (D-6, licensing) recorded as [ADR-0004](decisions/0004-licensing.md).

Decisions from here on get a record in [`decisions/`](decisions/) — what was chosen, what it costs, and what was rejected. Git history shows what changed; it does not show what was turned down or what the choice was expected to cost, and for a single-coder study holding its own hypotheses, the rejected alternatives are the part most worth being able to show.

### Resolved — now specified in the design (v0.4)

| Was                                                                                                             | Resolution                                                                                                                                       | Where it lives now                                    |
| --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------- |
| **D-1.** Procedure and checklist disagreed on when the design is frozen, leaving the registration SHA ambiguous | Two locks: **L1** design freeze before specimen selection, **L2** instrument lock after the both-arms gate. Separate frontmatter fields for each | Design → _Status_, _Procedure_, _Execution checklist_ |
| **D-4.** Nothing said which chunk a probe is answered against at A4                                             | The chunk containing the first character of the instance's host passage, plus a `spans_chunks` flag broken out in the H3 analysis                | Design → _What is scored at A4_, _Analysis plan_      |
| **D-5.** No rule for locating an instance inside an artifact                                                    | Per-arm anchors and host passages, resolved by script, verified for every instance before L2                                                     | Design → _Relation taxonomy_                          |
| **D-7.** The design's `MUST` → "needs to" is ungrammatical applied mechanically, in the implicit arm only        | D4 lowercases the keyword instead — RFC 8174 makes capitalization the marking. D4 instances reported separately from D3 within R3               | Design → _The marking manipulation_, _Analysis plan_; [ADR-0001](decisions/0001-lowercase-rfc2119-keywords.md) |

A fourth change went in alongside them: **D2, D3, and D4 insert language rather than only removing structure**, so the inserted wording now comes from a frozen, committed template set rather than being written per specimen. That is a constraint on W2 below, and the design states the consequence plainly — if exceptions turn out to be frequent, the mechanical-manipulation claim is false and gets reported as false.

The design's _What changed from 0.3_ section records all four. A fifth batch — the pilot carve-out, anchor timing and normalization, the procedure reorder, the A2 snapshot policy, the A3 extractor definition, and the foil cap — landed as **v0.5**; those are cited where they bind below.

### Resolved — engineering decisions

Not methodological. They change no claim and touch nothing registered, so they are recorded here and in `runlog.md` rather than in the design.

#### D-2. Language split — resolved: Node for the MDX transform, Python for everything else

The design says "a Python toolchain." That holds for the pipeline, coding harness, and analysis. The de-marking transform is the exception: it has to parse MDX with JSX component nodes — `<Tabs>`, `<TabItem>`, `<Steps>`, `:::caution` directives — and mutate an AST without disturbing anything else. Python has no MDX parser worth betting the manipulation's credibility on. `remark-mdx` / `mdast-util-mdx` is the same parser Astro itself runs. Regex over MDX source was rejected: the "Strawman implicit variant" threat is rated **High** in the design, and a hand-rolled parser makes that threat harder to rebut, not easier.

**Built**, at `pipeline/demark/` — TypeScript 7, unified 11 / remark-mdx 3, zod-validated template set, vitest suite, CLI with `normalize` and `demark` modes. Invoked as a subprocess by the Python driver. Its output is committed MDX, so the transform runs once and its results are reviewable as a diff — which is also the evidence that the manipulation was mechanical.

**It is implemented, not validated.** See `pipeline/demark/KNOWN-ISSUES.md`: DM-1 (nested containers are not de-marked) is blocking and must be fixed before L2; DM-2 (never run against real Astro MDX) closes at W1/W4.

#### D-3. A1 build strategy — ~~minimal Starlight harness~~ **superseded by [ADR-0003](decisions/0003-two-full-site-builds.md)**

> **Superseded.** A1 now comes from two complete builds of the same pinned docs tree. The harness decision below under-weighted O1 and O2: deixis and reference resolve against sidebar, breadcrumbs, prev/next links, and real cross-page hrefs, all of which a harness fabricates — and H2 is a hypothesis about deixis fragility. The W4 fidelity check would not have caught it, because it compared extracted A3 text and a missing sidebar does not show up there.
>
> Kept below for the record of what was considered.

Three options were considered:

1. **Build the full pinned `withastro/docs` site** with implicit variants added as additional pages. Highest fidelity — real Starlight config, real components, real CSS. Costs a working Astro build of a large third-party site, and adding pages perturbs sidebar/nav generation.
2. **Minimal Starlight harness**: a fresh Starlight project, specimens dropped into `src/content/docs/`, both arms as sibling pages. Cheap, reproducible, pinnable. Risks diverging from the real site's rendering if the docs repo overrides component behavior or theming.
3. Real site for the explicit arm, harness for the implicit arm — **rejected**: introduces a rendering difference between arms, which is precisely the confound the design exists to exclude.

**Decision: option 2, with a fidelity check against option 1 during the W4 pilot.** Build the harness, render one specimen through the real pinned site, and diff the extracted A3 text against the harness output for that specimen. If they match, the harness is validated and the finding is portable. If they diverge, record how, and either fix the harness config or fall back to option 1 — the fallback is still open at W4 because it is before L2.

Both arms build through the *same* harness with the same config. Pin Astro and Starlight in the harness lockfile and record the versions in `runlog.md`.

The check is not a formality: if the harness renders differently from the site the corpus was written for, every downstream artifact inherits that difference, and it would be discovered only when someone tried to reproduce the study.

#### D-8. Whether the explicit arm is round-tripped — **dissolved by [ADR-0002](decisions/0002-surgical-source-patching.md)**

> **Not settled as posed.** D-8 asked which of two bad options to take: leave a formatting confound in place, or round-trip the explicit arm so the noise is at least symmetric. ADR-0002 removes the confound instead — the transform patches source ranges by byte offset, so the explicit arm stays verbatim and the implicit arm differs only at de-marked sites. No design edit is needed, because the design's existing wording becomes literally true.
>
> The drift D-8 was worried about is real and measured: `*` bullets rewritten to `-`, table columns re-padded, the blank line after frontmatter dropped — all of which survive into A3.
>
> **D-8 reopens on its original terms if [spike 001](spikes/001-transform-architecture.md) fails.** In that case it gates L1, because the fallback does require a design edit.

#### D-6. Licensing — resolved: [ADR-0004](decisions/0004-licensing.md)

MIT for code, CC BY 4.0 for study data and instruments — and a **third scope** that only became visible on writing it down: `corpus/`, and corpus text reproduced inside `artifacts/`, stay under Astro's own MIT terms. They are not ours to relicense, and a blanket CC BY grant over `artifacts/` would have purported to do exactly that. `LICENSE` and `LICENSE-DATA` are written; `corpus/NOTICE` follows at W1, when there is a pinned SHA to name.

### Toolchain — resolved

`uv init` has been run. Python is **3.14**, pinned in `.python-version` and floored at `requires-python = ">=3.14"`. `inspect-ai 0.3.251` and `playwright 1.62.0` are resolved in `uv.lock` and installed, which discharges the earlier open question about Inspect's minimum Python — it installs and resolves on 3.14 alongside numpy 2.5.1.

Two follow-ups, both small and both W0:

- **`requires-python = ">=3.14"` is a floor, not a pin.** `.python-version` pins locally, but the study commits to publishing scripts someone else can run, and a floor lets a future interpreter resolve a different dependency set. Tighten to a bounded range (`>=3.14,<3.15`) so the published lockfile and the published `pyproject.toml` describe the same environment.
- **3.14 is recent enough to be a supply risk.** Everything resolves today; the thing to watch is a phase-2 dependency with no 3.14 wheel. Not a reason to downgrade — a reason to record the resolved versions in `runlog.md` now, so a later failure is diagnosable rather than mysterious.

---

## 2. Milestones

Milestones are numbered **W0–W10** — work packages — not M0–M10 as before: the design's measure IDs own the M namespace, and "M8 — M2 redundancy inventory" was reading as nonsense. Locks stay L1/L2; spikes keep their names.

Ordering is a dependency graph, not a wish list. **L1 gates W1. L2 gates W6.** Nothing downstream of a lock may loop back without an amendment entry.

### W0 — Repository foundation

Everything here is pre-registration housekeeping. **Partly done** — `uv init` and the Node package have landed, but nothing is committed yet.

Done:

- ✅ Python toolchain: 3.14 pinned, `pyproject.toml`, `uv.lock`, `.venv`, `inspect-ai` and `playwright` resolved.
- ✅ Node package at `pipeline/demark/` — see D-2. Prototype architecture; being rebuilt per ADR-0002.
- ✅ `decisions/`, `spikes/`, `IMPLEMENTATION_PLAN.md`, `README.md`.

Outstanding:

- **A root `.gitignore`. Do this before the first commit** — there is none, and `pipeline/demark/node_modules/` is currently not ignored, so a naive `git add -A` commits several hundred packages into the registration record. Needs `node_modules/`, `dist/`, `*.tsbuildinfo`, `__pycache__/`, `build/`, and the generated implicit tree from ADR-0003. (`.venv/` self-ignores — uv writes `.venv/.gitignore`.)
- **The first commit.** `main` still has zero commits.
- Copy the design in (v0.5) as `DESIGN.md`; strip the blog-specific `{# ... #}` author comments or convert them to a `TODO.md` — they are notes to a writer, not part of a registration.
- Add a remote and set `repository:` in frontmatter to it. Currently there is none.
- `AMENDMENTS.md` (header + empty table) and `runlog.md`. ✅ `.gitignore`, `LICENSE`, `LICENSE-DATA`.
- Tighten `requires-python` per *Toolchain* above; replace the `uv init` placeholder `description`.
- Decide where Python lives (below), then lay out the rest of §4.
- `Makefile` or `justfile` for the stage commands.
- CI running formatting, type checks, and both test suites. Cheap, and it means the published scripts are demonstrably runnable by someone else.

#### Where Python code lives

`uv init` created an installable package at `src/docs_transduction_study/` with a placeholder `main()` and a `[project.scripts]` entry point. That is a better home for the stage drivers than the loose `pipeline/*.py` and `analysis/*.py` files §4 originally described — importable, testable, and it gives the pipeline stages a single namespace instead of a directory of scripts that only run from the repo root.

Adopting it means **separating code from data**, which §4 below now reflects:

- **Code** — `src/docs_transduction_study/` (Python) and `pipeline/demark/` (Node).
- **Data and outputs** — `corpus/`, `artifacts/`, `instruments/`, `coding/`, `logs/`, `figures/`.

That split is worth having for its own sake in a study that publishes its dataset: a reader can tell at a glance what is an instrument and what is a result. The design's *Data management* block already reflects it.

**Exit:** `main` has commits; `.gitignore` covers every generated tree; `make help` lists every stage command as a stub; resolved toolchain versions recorded in `runlog.md`.

### L1 — Design freeze

Commit; record date and SHA in `DESIGN.md` frontmatter and in `runlog.md`. From here, hypotheses/taxonomy/rubric/rules changes are amendments.

### W1 — Corpus acquisition and specimen selection

- Vendor `withastro/docs` at a pinned SHA. **Git submodule, not a clone** — the SHA is then a first-class object in this repo's history, which is exactly the auditability the design wants. Record the SHA in `runlog.md` on the day it is pinned. **The pin itself lands pre-L1 as spike prep (§7)**; what L1 gates is selection.
- `corpus.py`: enumerate candidates under `src/content/docs/en/`, emit component-usage counts per page (Steps, Tabs, Asides, tables, normative keywords) so selection is informed by where the manipulated relations actually live.
- Select 8–12 specimens by hand against the design's rules (spans Diátaxis types, records last-major-change version). Selection is a judgment call; the _rationale per specimen_ is the artifact that makes it inspectable.
- Copy specimens to `corpus/explicit/` verbatim.

**Exit:** `corpus/specimens.csv` complete with rationale and change-version columns; component-count report committed.

### W2 — De-marking transform (implicit arm)

The highest-risk code in phase 1. **Runs after [spike 001](spikes/001-transform-architecture.md)**, which decides whether the architecture below is the one that gets built.

- Node package implementing D1–D4 and D7 as remark/mdast transforms, **patching source ranges by byte offset rather than re-serializing the document** ([ADR-0002](decisions/0002-surgical-source-patching.md)). The explicit arm is then verbatim Astro source and the implicit arm is byte-identical to it except at de-marked sites.
- Rules descend recursively, which is required by patching and is also what closes DM-1. Do not fix DM-1 separately — it closes when this lands.
- A first version exists at `pipeline/demark/` on the older whole-document architecture. Treat it as a prototype: the rules, template loading, and test suite carry over; the traversal and serialization do not.
- **The templates are the manipulation**, and the design now requires this rather than merely permitting it. D2, D3, and D4 insert words; those insertions come from a small, fixed, committed template set applied uniformly, never per-specimen. Templates live in `pipeline/demark/templates.json` and are frozen at L2. Exceptions are logged with the specimen named — and per the design, frequent exceptions falsify the mechanical-manipulation claim and get reported as such.
- Output to `corpus/implicit/`, committed, so `git diff` between arms is the reviewable record of what the manipulation did.
- **Propositional-equivalence review**: read every diff hunk against the constraint that no information — including relational information — was dropped. Log per-specimen sign-off. This is manual and it is the point. Under ADR-0002 the diff carries the manipulation and nothing else, which is what makes the review worth trusting.
- Both arms must build clean (W4 dependency; iterate).

**Exit:** implicit arm generated purely by committed script + templates; equivalence review logged; zero hand edits (provable from history).

### W3 — Relation inventory

- Walk both arms; classify R1–R4 from component/keyword sites, O1–O2 from candidate referring and deictic expressions.
- R1–R4 detection can be largely automatic from the explicit arm's component tree — a `<Steps>` block _is_ an R1 instance. O1/O2 need analyst judgment with an assist script surfacing candidates.
- Populate `instances.csv` including per-arm anchors and host passages (D-5).
- **Check cell minimums now**: ≥20 instances per type across R1–R4 and O1–O2. If a cell is short, that is discovered here — and the design requires the shortfall be recorded _before running_, not after. Widening specimen selection is legitimate at this point; it is not after L2.

**Exit:** `instances.csv` complete; anchors resolve in both arms at A0; cell counts recorded.

### W4 — Pilot (throwaway, and disposed of on the record)

Now in the design — v0.5's pilot carve-out. One page, three disposable probes, straight through A1→A4 and a coding dry run.

Purpose: surface the things that only appear when the pipeline runs — Starlight version quirks, accessibility-tree shape for tabs, whether the chunker's parameters produce sane units, whether the coding UI is usable for an hour without error. Discovering any of those _after_ L2 costs an amendment.

**The pilot page is not one of the selected specimens.** The v0.5 carve-out requires that the author see no study specimen's downstream artifacts before L2 — a non-sample page answers every engineering question the pilot has. Pilot artifacts and probes are **discarded and never reused**, and the disposal is logged in `runlog.md` with its date.

Spike 001 answers the architecture questions before this point. What remains for the pilot is what only a full run shows: build determinism across runs, how much theme chrome survives A3 extraction into the A4 chunks, and whether the coding UI is usable for an hour without error.

**Exit:** end-to-end run completes; pilot artifacts and probes deleted; findings logged.

### W5 — Probe authoring and the gate

- `instruments/probes.csv`: one row per instance — question, correct answer, one or more foils, `"The text does not say"` implicit, `version_change` flag.
- Authoring rules enforced by a linter, not by memory: exactly one probe per instance; no probe string appears verbatim in either arm's source (the distinctive-string rule, checkable now that both arms exist — this is why the design reordered); foils are relations, not paraphrases of absence.
- **The gate**: answer every probe from both A0 variants. Failures excluded, with reason, into `instruments/gate_exclusions.csv`. Exclusions happen before the lock or they are not exclusions.
- Designate the version-change subset against specimen change-versions from W1. **Every `superseded_answer` is verified against a pre-change source** — the docs tree at a pre-change SHA, or the changelog entry for the breaking change — and that source is recorded per probe in `superseded_source`. An unverified superseded answer is not a version-change probe.
- Generate and record the coding-order seed.

### L2 — Instrument lock

Commit `specimens.csv`, `instances.csv`, `probes.csv`, `gate_exclusions.csv`, `templates.json`, the seed. Record SHA in frontmatter and `runlog.md`. **No artifact is generated before this commit exists.**

### W6 — Pipeline A1–A4

One driver, four deterministic stages, both arms, all committed.

| Stage | Implementation                                       | Watch for                                                                                                                                                           |
| ----- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A1    | Two full `astro build` runs of the pinned docs tree, explicit and implicit ([ADR-0003](decisions/0003-two-full-site-builds.md)) | Identical page sets and routes in both; record Node version, package manager, and build determinism                                                                 |
| A2    | Playwright accessibility snapshot of the served page, **default page state, no interaction** — the design's registered policy | Inactive tab panels are typically *absent* from the accessibility tree, not flattened — so R2 evidence may die at A2, not A3. The pilot confirms the shape so it cannot surprise the analysis |
| A3    | HTML → text, from the article element only, via a **named, versioned extractor in plain-text (no-markup) mode** | Config recorded; this matches the design's A3 definition. A bespoke tag-stripper makes A3 a study artifact rather than a realistic stage; full-page extraction pulls in sidebar, header, footer, and search chrome |
| A4    | Fixed-size, no-overlap chunker, **character-based, not token-based** — a tokenizer would smuggle a model-family artifact into the model-free phase 1 | Parameters recorded, script committed, chunk size justified in `runlog.md` as a configured choice — the design already concedes this is a configuration, not a fact |

Then `anchors.py` locates every instance in every artifact and emits the per-instance A4 chunk selection plus `spans_chunks` per D-4.

Anchor matching runs through the **committed normalization spec**, frozen at L2 — smart quotes, dash conversion, entity encoding, and markup stripping break verbatim matching on ordinary pages, so exact-match resolution would fail for boring reasons. An anchor that fails to resolve after L2 is repaired as a **mechanical amendment** per the design (results-not-seen). The exit criterion below means 100% *after normalization, with any repairs logged* — not that failures are unrepresentable.

**Exit:** `artifacts/` populated for both arms at A1–A4; anchor resolution 100% at A1–A3; A4 chunk assignment complete.

### W7 — Coding harness and M1a

The phase-1 deliverable. A small local CLI — no network, no model, no framework. **Two entry points, so the sealing contradiction cannot exist in one program:**

- **`setup` — run once.** Reads `instances.csv` + `probes.csv` + the artifact tree, shuffles by the recorded seed across specimen × stage × arm, renames artifacts to opaque IDs, writes `artifacts/manifest.csv`, and **encrypts the mapping at rest in the repo**, with the ciphertext checksum recorded in `runlog.md`. It is decrypted once, at analysis, and the decryption date is logged.
- **`code` — the coding session.** Presents artifact + question + randomized options; captures the choice and, for correct answers, the **explicit vs. inferred** flag that separates Preserved (3) from Degraded (2). Its read path contains no mapping — it is structurally incapable of resolving an opaque ID, which is what §6 requires.

- Appends to `coding/m1a.csv`. **Append-only, enforced in code** — a re-code writes a new row with its own timestamp and `pass` number; nothing is ever updated in place.
- Run M1a to completion. Then wait **≥7 days** and re-code a 20% sample; `analysis/` computes intra-rater kappa.
- If kappa < ~0.6: report the instrument failure and stop. The design commits to this; the code should make it easy to honor rather than easy to rationalize.

**Exit:** M1a complete; re-code done after the real interval; kappa computed and recorded.

### W8 — M2 redundancy inventory

Analyst-side, model-free, independent of W6/W7 — **can run in parallel from W3 onward**, an ordering design v0.5 now explicitly permits. For each relation instance, record which of three channels carry it: documentation, CLI surface (help output, flag names, error strings), runtime behavior. Output `coding/m2_redundancy.csv` and the redundancy map.

Requires actually installing and running Astro's CLI to observe channels 2 and 3. Budget for it; it is the only part of phase 1 that touches the product.

### W9 — Phase 1 analysis

- `analysis/` producing, per the pre-specified plan: survival by arm × stage pooled **and per specimen**; the trajectory figure with both arms overlaid; per-stage gap; H2 fragility by observed type; H3 Corrupted:Absent ratio at A4 with `spans_chunks` broken out; M2 redundancy map.
- Distributions and raw counts, not just means. Effect sizes lead.
- Everything not in the plan is emitted into a separate `exploratory/` output directory so the labeling is structural rather than remembered.

**Exit:** figures and tables sufficient to draft part 3; dataset, scripts, and run log publishable.

### W10 — Phase 2 (deferred, gated on phase 1 shipping)

Inspect AI tasks for A5 generation, M1b, and the closed-book covariate — **two tasks over one shared dataset definition**, as the design requires, so a probe amendment cannot propagate to one and not the other. Pin the Inspect version alongside model IDs and temperature. Declare the epoch reducer before running. Publish the eval logs.

---

## 3. Data contracts

Fixing these now is most of what makes the milestones parallelizable. All CSVs, UTF-8, committed.

**`corpus/specimens.csv`** — `specimen_id`, `source_path`, `diataxis_type`, `last_major_change_version`, `selection_rationale`

No `pilot` column: the v0.5 carve-out means the pilot page is never a specimen. It is identified in `runlog.md` at W4, alongside the disposal entry.

**`instruments/instances.csv`** — `instance_id`, `specimen_id`, `relation_type` (R1–R4, O1, O2), `anchor_explicit`, `anchor_implicit`, `host_passage_explicit`, `host_passage_implicit`, `demark_rule` (D1–D4/D7, or blank for observed), `notes`

**`instruments/probes.csv`** — `probe_id`, `instance_id`, `question`, `correct_answer`, `foil_1`, `foil_2` (two is the cap, per design v0.5), `version_change` (bool), `superseded_answer`, `superseded_source` (version-change probes only: the pre-change docs SHA or changelog entry the superseded answer was verified against)

`"The text does not say"` is appended at presentation time, never stored as a column — it must be identically worded on every probe.

**`instruments/gate_exclusions.csv`** — `instance_id`, `reason`, `failed_arm`, `date`

**`artifacts/manifest.csv`** — `artifact_id` (opaque), `specimen_id`, `arm`, `stage`, `path`, `chunk_index` (A4 only), `spans_chunks` (A4 only). **Mapping encrypted at rest until analysis** (W7).

**`coding/m1a.csv`** (append-only) — `row_id`, `timestamp`, `session_id`, `pass` (1 or 2), `artifact_id`, `probe_id`, `selected_option`, `support` (`explicit` | `inferred` | n/a), `score` (3/2/1/0, derived), `coder_id`

**`coding/m2_redundancy.csv`** — `instance_id`, `channel_docs`, `channel_cli`, `channel_runtime` (each bool), `evidence_note`

Score derivation is a pure function of `selected_option` + `support`, implemented once and unit-tested, so no scoring discretion exists anywhere downstream of the coder's click.

---

## 4. Repository layout

Extends the design's layout with the engineering directories it implies but does not enumerate. **Code and data are separate** — see W0.

```
── Registration and record ────────────────────────────────────────
DESIGN.md                  Frozen at L1. Authoritative.
AMENDMENTS.md              Post-L2 changes: date, change, rationale, results-seen
runlog.md                  Chronological; every deviation, version, and pin
README.md                  Public-facing summary
IMPLEMENTATION_PLAN.md     This file. Not part of the registration.
decisions/                 Numbered decision records. Not part of the registration.
spikes/                    Throwaway investigations; findings land in runlog.md
LICENSE / LICENSE-DATA

── Code ───────────────────────────────────────────────────────────
pyproject.toml  uv.lock  .python-version      Python 3.14, pinned
src/docs_transduction_study/
  corpus.py                Specimen selection and the pinned-SHA record
  demark.py                Subprocess driver for the Node transform
  stages/                  a1_build, a2_a11y, a3_text, a4_chunk
  anchors.py               Instance resolution; A4 chunk assignment
  coding.py                M1a harness — setup + code entry points, append-only log
  analysis/                Pre-specified analyses; exploratory/ kept separate
  inspect/                 Phase 2 tasks, solvers, scorers; A5 prompt
tests/                     Python test suite
pipeline/demark/           Node: remark-mdx transform + templates.json
                           KNOWN-ISSUES.md — open defects, must clear before L2

── Data and outputs ───────────────────────────────────────────────
vendor/astro-docs/         Submodule, pinned SHA — the explicit tree
build/                     Generated implicit tree (gitignored)
corpus/
  specimens.csv
  explicit/                Verbatim specimens
  implicit/                Script-generated variants
instruments/               instances.csv, probes.csv, gate_exclusions.csv, rubric.md
artifacts/                 A1–A4 output, opaque IDs; mapping encrypted until analysis
coding/                    m1a.csv (append-only), m2_redundancy.csv, seed
logs/                      Inspect eval logs, published
figures/                   Generated figures
```

---

## 5. Rough sizing

Order-of-magnitude, for sequencing rather than scheduling.

| Milestone | Effort                                                | Note                                      |
| --------- | ----------------------------------------------------- | ----------------------------------------- |
| W0        | ~0.5 day remaining                                    | Python and Node toolchains already landed |
| W1        | 1–2 days                                              | Selection judgment is most of it          |
| Spike 001 | 2 days, timeboxed                                     | Gates W2's architecture and W6's build strategy |
| W2        | 4–6 days                                              | Surgical patching is more work than serializing; prototype rules carry over |
| W3        | 2–3 days                                              | O1/O2 classification is manual            |
| W4 pilot  | 1–2 days                                              | Pays for itself                           |
| W5        | 3–4 days                                              | ~120–200 probes, each gated twice         |
| W6        | 2–3 days                                              | Mostly plumbing; A2 may surprise          |
| W7        | 2 days build, then **coding time + a hard 7-day gap** | The re-code interval is real elapsed time |
| W8        | 1–2 days                                              | Parallelizable from W3                    |
| W9        | 2–3 days                                              |                                           |

The critical path is corpus pin + fixture pages → spike 001 → L1 → W1 → W2 → W3 → W5 → L2 → W6 → W7, with the ≥7-day re-code interval as an unavoidable wall-clock cost that should be planned around rather than absorbed at the end.

The spike sits **before L1** deliberately. Two days spent there is cheaper than rewriting the transform after discovering that offsets do not hold on real nested MDX — and with the spike ahead of the freeze, a failure costs an edit to an unfrozen design rather than a retaken registration.

---

## 6. Implementation risks

Distinct from the design's validity threats — these are ways the _build_ fails.

| Risk                                                                               | Mitigation                                                                                                                                                                                                         |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| The de-marking transform needs per-specimen tuning to produce readable MDX         | Freeze templates at L2 and treat any needed exception as an amendment with the specimen named. If exceptions are frequent, the mechanical-manipulation claim is false and that must be reported, not patched over. |
| Cell minimums unreachable from 8–12 specimens                                      | Discovered at W3, before L2, when widening selection is still free                                                                                                                                                 |
| Astro's `<Steps>` and `<Tabs>` compile to markup the a11y snapshot flattens anyway | Detect at W4 pilot; it is a finding about A2, not a blocker, but it should not be a surprise at analysis                                                                                                           |
| Coding fatigue degrades later scores                                               | Randomized order already spreads this across cells; cap sessions and record `session_id` in `m1a.csv`                                                                                                              |
| Sealed mapping leaks into the working tree                                         | The mapping is encrypted at rest with its checksum in `runlog.md` (W7); the `code` entry point's read path contains no mapping and cannot resolve an opaque ID                                                     |
| Phase 2 blocked by Inspect API drift, or a phase-2 dependency with no Python 3.14 wheel | Versions pinned in `uv.lock` and recorded in `runlog.md`; verify Inspect's current API against its documentation, not from memory                                                                             |

---

## 7. Immediate next actions

1. **Make the first commit.** `main` still has zero commits. `.gitignore` is in place, so `git add -A` is now safe.
2. **Finish W0**: `DESIGN.md` (v0.5), `AMENDMENTS.md`, `runlog.md`, remote, CI.
3. **Pin the corpus and pull a few real pages as engineering fixtures** for the spike. This is not specimen selection — selection stays gated on L1. Fixtures are pages the spike parses and patches, chosen for component density, and discarded after.
4. **Run [spike 001](spikes/001-transform-architecture.md)**, then rebuild the transform per whichever architecture survives it.
5. **Take L1.** An earlier revision of this plan claimed nothing gated it; that was wrong twice over. The pre-L1 design-edit batch gated it — pilot carve-out, anchor timing, procedure reorder, now landed as v0.5 — and the spike gates it still, because a spike failure reopens D-8 with a design edit attached.
6. **W1** — formal specimen selection.

**Do not fix DM-1 on its own.** The nesting bug and the formatting confound are the same architectural problem, and ADR-0002 closes both. Patching it separately means writing recursive descent twice.

**If spike 001 fails**, D-8 reopens on its original terms with a design edit attached. With the spike ahead of L1, that costs an edit to an unfrozen design rather than a retaken registration — which was the whole argument for moving it.

**Note on sequencing.** The de-marking transform (W2) was built ahead of W0 and W1. That is workable — it is pure logic, testable on synthetic fixtures — but its correctness means "matches how Astro actually writes MDX," which cannot be established until specimens exist. Treat it as implemented and **unvalidated** until DM-2 is closed at W1/W4, and expect its traversal and serialization to be replaced wholesale by ADR-0002.
