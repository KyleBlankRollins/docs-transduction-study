# Communicability Under Transduction

A pre-registered experiment testing whether **explicitly marked pragmatic relations survive a documentation delivery pipeline better than the same relations left implicit in prose**.

> **Status: registered and run, with AI-assisted execution. Results are exploratory.**
>
> Registered 2026-08-02 and instrument locked 2026-09-23. The planned human coding was replaced by AI evaluators (amendment A3). The run used GLM-5.3-Flash on 2026-09-24 and was replicated with Claude Sonnet 5.5 on 2026-11-18 (A9). Every result here is model-conditioned and was scored under amendments decided after partial exposure. Read [Where things stand](#where-things-stand) before citing anything. Design version 0.9 plus post-lock amendments A5–A10.

---

## Where things stand

The design below is the one registered. The execution departed from it in one large, logged way. Amendment A3 replaced the human analyst with AI evaluators, because human coding time was not available. That forfeits the model-free, training-data-immune Phase 1 claim.

**What was run (measure M1-AI):**

- 229 relation instances on 12 Astro pages.
- Both arms at stages A1–A4: 1,832 forced-choice assignments, plus a seed-selected 20% repeat pass (367).
- Each assignment was evaluated in a fresh, isolated context with no answer key.
- Two evaluator families, never pooled:

| Evaluator | Run | Coverage | Repeatability (kappa) |
| --------- | --- | -------- | --------------------- |
| GLM-5.3-Flash (OpenCode) | 2026-09-24, pre-specified | 1,827 / 1,832 | 0.668 |
| Claude Sonnet 5.5 (Message Batches) | 2026-11-18, replication (A9) | 1,827 / 1,832 | 0.848 |

**What it found.** These are explicit-minus-implicit mean scores on the 0–3 rubric, A7 scoring. A negative value means the implicit, prose arm scored higher.

| Stage | GLM-5.3-Flash | Claude Sonnet 5.5 |
| ----- | ------------- | ----------------- |
| A1 compiled HTML | −0.147 | −0.052 |
| A2 accessibility tree | −0.099 | −0.057 |
| A3 plain text | −0.071 | −0.096 |
| A4 retrieval chunk | −0.044 | −0.024 |

- **H1 is not supported under either evaluator.** Explicit marking shows no survival advantage at any stage, and the gap does not widen down the pipeline. The two evaluators agree on the sign at every stage, a comparison pre-specified in A9.
- **The gap is about quotability, not correctness.** The share of correct answers differs between arms by under two percentage points at every stage, under both evaluators. Nearly all of the gap lies between scores 2 and 3: correct answers backed by a quotable explicit statement versus correct answers reached by inference. Prose states a relation in a sentence that can be quoted, while markup carries it in structure. For GLM this was found by unplanned diagnostics; for Claude the correctness comparison was pre-specified.
- **H3 is not supported.** At the chunk stage, a lost relation more often became a visible gap than a wrong one: 6 Corrupted versus 42 Absent under GLM, and 5 versus 43 under Claude.
- **Not summarized here:** H2 (deixis) and the R3 device breakdown. See the tables in `analysis/`. Human M1a/M1b coding and Phase 2 were not run, and M2 is only a partial inventory.

**Why caution is warranted.**

- These are judgments by models whose training data very likely includes this corpus.
- The quote-verification rule (A7) and the coverage rules (A8, A10) were set after partial exposure to the outputs. Each amendment says exactly what had been seen.
- The rubric's "explicit support" criterion may itself favour prose.

Details: [`AMENDMENTS.md`](AMENDMENTS.md), [`runlog.md`](runlog.md), `analysis/m1_ai_a7/` (GLM), `analysis/m1_ai_a7_claude-sonnet-5-5/` and `analysis/replication_claude-sonnet-5-5/` (Claude), and `analysis/exploratory/` (unplanned).

## What this is

Technical writing advice increasingly says to mark things explicitly — use step components, use admonitions, use `MUST` rather than "should probably" — because documentation now passes through pipelines before anyone reads it: rendered to HTML, flattened to text, split into retrieval chunks, summarized by a model.

That advice is plausible, widely repeated, and undemonstrated. This experiment is an attempt to demonstrate it or fail to.

It is a small, single-coder study on one corpus. It is designed to produce a defensible answer to a narrow question, not a general theory of documentation. The pre-registration exists because the author selected the corpus, wrote the measuring instrument, and holds the hypotheses — which is exactly the situation where a design frozen in advance is worth more than a good intention.

## The question

Four literatures — Morris's semiotics, Kress's social semiotics, Jorna and van Heusden on representation, Goodman on notation — argue that meaning is remade whenever a representation is transformed. None of them measured it on documentation.

**The recommendation under test:** that marking relations with component syntax, structural markup, and controlled vocabulary makes those relations survive the pipeline better than carrying them in well-written prose.

## The design in one paragraph

Take real documentation pages. Produce a second variant of each that says exactly the same things but carries its relations in prose instead of structure. Push both variants down the same pipeline. At each stage, ask a fixed set of locked multiple-choice questions and record whether the correct answer is still recoverable.

**The finding is the divergence between the two trajectories, not the performance of either arm.** Both arms start equal at the source by construction — every probe is verified answerable from both variants before anything is locked. Any gap that opens downstream was caused by the pipeline acting on the marking difference, because nothing else differs.

### A concrete example

Astro's install instructions render three package-manager commands as tabs. Tabs encode a **membership** relation: these are alternatives, run exactly one.

Strip the tab structure in plain-text extraction and you get three consecutive command blocks, which read as a **sequence**: run all three, in order.

That is not information loss in the usual sense. The words all survived. The relation was silently replaced with a different, wrong relation, and nothing in the output marks the substitution. A reader — human or machine — has no signal that anything went missing.

Measuring how often that happens, and whether explicit marking prevents it, is the entire study.

## What gets varied, and what doesn't

**Manipulated relations** — marked by Starlight components, mechanically de-markable without touching content:

| ID | Relation | Explicit marking | Implicit carrier |
| -- | -------- | ---------------- | ---------------- |
| R1 | Sequence | Step components | Prose paragraph, order in sentence sequence |
| R2 | Membership | Tabbed panels | Prose enumeration |
| R3 | Force | Admonitions, normative keywords | Modal verbs in running prose |
| R4 | Precondition | Prerequisite blocks, tables | Prose statement in place |

**Observed relations** — naturally occurring, identical in both arms, tracked but never manipulated:

| ID | Phenomenon | In documentation |
| -- | ---------- | ---------------- |
| O1 | Reference | "the key," "your existing config" |
| O2 | Deixis | "this step," "as described above" |

Reference and deixis are the two categories the LLM pragmatics literature flags as most fragile, and they are deliberately **not** manipulated — you cannot de-mark a referent without changing what the text says, which would violate the equivalence constraint the whole design rests on.

## The pipeline

| ID | Stage | Nature |
| -- | ----- | ------ |
| A0 | Authored MDX | Reference. Probes gated here. Not scored. |
| A1 | Compiled HTML | Deterministic |
| A2 | Accessibility tree | Deterministic |
| A3 | Plain-text extraction | Deterministic |
| A4 | Retrieval chunks | Deterministic |
| A5 | Model summary | Stochastic — phase 2 only |

Every stage is study-controlled, and both arms pass through all of it.

At the page-level stages the artifact is the whole page. At the chunk stage it is **one chunk — the one containing the start of the passage the probe is about** — fixed as a rule before any artifact exists, because "which chunk did you look at?" would otherwise decide the answer after the fact. Where that passage is cut across a chunk boundary, the split is recorded and analyzed rather than avoided: a relation whose evidence was halved, with nothing left to mark the amputation, is the failure mode the study is looking for.

## How survival is scored

One locked, closed-form probe per relation instance, with pre-written wrong answers:

> **Probe:** Are the three package-manager commands alternatives to each other, or steps to run in sequence?
> **Correct:** Alternatives — run exactly one.
> **Foil:** Sequence — run all three in order.
> **Always available:** "The text does not say."

| Score | Label | Meaning |
| ----- | ----- | ------- |
| 3 | Preserved | Correct, supported explicitly |
| 2 | Degraded | Correct, but only by inference |
| 1 | Absent | "The text does not say" — the loss is visible |
| 0 | Corrupted | A foil — a wrong relation is supported, and nothing signals it |

**Corrupted scores below Absent deliberately.** A reader who can't form an interpretation fails loudly and recoverably. A reader who confidently forms the wrong one fails silently. Pooling those two outcomes would discard the result this study most wants to see.

Scoring is exact match against locked options. There is no judge model and no free-text interpretation — using a model's pragmatic competence to measure pragmatic failure would be circular, and letting the author interpret free-text answers would reimport the bias the instrument exists to remove.

## Hypotheses

| ID | Hypothesis | Disconfirmed if |
| -- | ---------- | --------------- |
| H1 | The survival gap between arms **widens** down the pipeline | Trajectories stay parallel, or implicit survives equal or better at every stage |
| H2 | Deixis (O2) is the most fragile type, and chunking is where it breaks | Another type is reliably more fragile, or deixis survives chunking comparably |
| H3 | At the chunk stage, loss more often produces a *wrong* relation than a visible gap | Absence dominates, or the two are comparable |
| H4 | *(Phase 2)* Prior intrusion rises as artifact recoverability falls | Intrusion is flat or falls |

**H1 is the recommendation under test.** If it fails, the practical advice the surrounding blog series gives is unsupported in the form it is stated, and the series has to say so.

## What would prove this wrong

Committed in advance, and every one of these will be published if it happens:

- **Trajectories run parallel.** Marking never mattered. The central recommendation is unsupported.
- **The gap opens only at the summary stage.** The argument is about summarization, not transduction generally.
- **The gap is fully present at plain-text extraction and grows no further.** The argument is about one fixable pipeline stage, not about writing.
- **Deixis survives fine.** A convergence between two literatures, currently treated as strong evidence, is unsupported by direct measurement.
- **Absence dominates corruption.** The silent-failure argument is weaker than claimed.
- **Intra-rater kappa below ~0.6.** The instrument is too noisy. The failure gets reported; the findings do not.

A null result is worth more here than a confirmation, because nobody has measured this at all.

## What this is not

- **Not an application of the Semiotic Inspection Method or the Communicability Evaluation Method.** SIM compares sign classes within one system, qualitatively. CEM requires an observed interpreter acting under a fixed utterance vocabulary. This study does neither. What it takes from semiotic engineering is *communicability* as the measured construct, the analyst-side stance, and the loud/silent breakdown distinction — and it says so rather than borrowing methodological credibility it hasn't earned.
- **Not a benchmark of any model, vendor, or product.** Phase 2 uses models as instruments, not as subjects. The annex snapshot of a third-party retrieval service is dated, observational, and makes no comparative claim.
- **Not a claim about documentation in general.** One product, one docs team, one house style. It demonstrates a mechanism; it does not estimate a population.
- **Not a critique of Astro's documentation.** The corpus was chosen *because* it is well written and well marked. The implicit variants are constructed by this study, not found in the wild, and they are not how Astro's docs are written.

## Repository layout

```
DESIGN.md              The design, frozen at registration (v0.9). Authoritative.
AMENDMENTS.md          Every post-registration change, logged (A1–A10)
decisions/             Architecture decision records (ADR-0001 to 0005)
vendor/astro-docs/     withastro/docs submodule, pinned at 6eca24e7
corpus/                Selected specimens, both arms (explicit verbatim, implicit de-marked)
pipeline/              De-marking transform (TypeScript) and the build overlay
instruments/           Instances, probes.csv (questions, answers, foils), gate evidence and exclusions
artifacts/             A1–A4 artifacts, assignment packets, sealed answer keys (large files via Git LFS)
coding/                M1-AI records, append-only (GLM in coding/, Claude in coding/claude-sonnet-5-5/); M2 inventory
analysis/              Pre-specified M1-AI tables per evaluator, replication comparison, exploratory diagnostics
src/, tests/           Python pipeline, runners, scoring, and analysis; `make check`
runlog.md              Reverse-chronological, including every deviation
```

Phase 2 (`inspect/`, `logs/`) has not been built.

Coding records are **append-only**. Scores are never overwritten; a re-code adds a row with its own timestamp so the intra-rater comparison stays reconstructable.

## Phases

> Superseded in part by amendment A3. Phase 1 was executed by AI evaluators, not an analyst, so its findings are model-conditioned and do not have the properties claimed below. The original plan is kept so the departure stays auditable.

**Phase 1 — analyst-judged survival + redundancy inventory.** Fully offline. Zero model dependencies. No sandbox. Stages A1–A4, both arms. This is a complete study on its own, and its findings are claims about artifacts, which do not expire when models change.

**Phase 2 — model summaries, model-judged probes, contamination measurement.** Adds ≥3 models across ≥2 vendors. Only the *divergence* between arms is carried forward as a claim, never absolute scores.

The split is deliberate: **if phase 2 never happens, phase 1 still stands.**

### Tooling

**Phase 1 uses no evaluation framework and makes no network calls.** It is an analyst reading artifacts and choosing among locked options. That is what makes its findings claims about artifacts rather than about models, and it is why nothing in phase 1 should be reshaped into an eval task for the sake of toolchain consistency.

**Phase 2 runs on [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai)** (UK AI Security Institute, MIT, Python). This is a pragmatic choice, not an architectural one — the design does not depend on it:

- **A forced-choice probe is Inspect's native task shape.** Choice-style solver, exact-match scorer against the locked answer key, no custom judge anywhere in the loop.
- **Multi-model replication is a config change** rather than per-vendor API code — and the only durable claim phase 2 makes is that the H1 divergence replicates across models and vendors.
- **Epochs with a reducer declared before running** handle stochasticity without a post-hoc aggregation choice, which would otherwise invite the charge of having picked the flattering one.
- **The logs are publishable as-is.** Structured, carrying full transcripts and model config, built to be reopened by someone else. A hand-rolled harness would make the logging format itself something a reader has to take on trust.

One integrity detail worth stating here rather than burying in the design: **the model-judged pass and its closed-book covariate are built as two tasks over a single shared dataset definition.** The covariate is the same probe set with no artifact attached. Sharing the definition means a probe amendment propagates to both tasks or to neither, so the covariate cannot silently drift out of sync with the main run and the contamination comparison stays like-for-like by construction.

The Inspect version is pinned and recorded alongside model IDs. The server-mediated annex needs no framework — it is a locked query set and verbatim archived responses.

## Pre-registration protocol

This is the part that separates a study from a story, so it is worth being explicit about the mechanics:

Registration happens in **two locks**, because two different things need protecting and they are ready at different moments.

1. **The design freeze.** The hypotheses, taxonomy, rubric, de-marking rules, and analysis plan are committed and the SHA recorded — before a single specimen is selected. This is what stops hypotheses being fitted to data.
2. **The instrument lock.** The specimen list, relation inventory, probes with their foils, the gate exclusions, the de-marking templates, and the coding-order seed are committed and that SHA recorded too. This happens later, because probes cannot be written until both variants exist — the rules that probes may not quote distinctive strings and must be answerable from both arms are only checkable against real text. This is what stops the instrument being fitted to the artifacts.
3. **No artifact is generated before the instrument lock commit exists.** Each probe is verified answerable from **both** source variants first; instances that fail that gate are excluded and logged — before locking, not after.
4. After each lock, any change to what it covers goes in `AMENDMENTS.md` with the date, the change, the rationale, and **whether any results had been seen at the time**.
5. An amendment made after seeing results is not disqualifying. An *unlabeled* one is.
6. Everything not in the pre-specified analysis plan is exploratory and labeled as such in publication.

The Git history of this repository is the registration record. That is the whole reason the experiment lives in its own repo.

## Corpus and attribution

Specimens are drawn from the **Astro documentation** ([`withastro/docs`](https://github.com/withastro/docs), `src/content/docs/en/`, MDX with Starlight components), pinned to a commit SHA recorded at registration.

Astro's documentation is MIT licensed, which permits publishing specimens and derived variants with attribution. The implicit-arm variants in this repository are **derivative works created by this study** and are not Astro's documentation. They are mechanically degraded on purpose, and should not be read as representative of the project's writing.

The corpus was chosen because it is not the author's own writing, because its component-based markup makes the manipulation mechanical rather than editorial, and because a real version history makes training-data contamination measurable rather than merely acknowledged.

## Before you trust this

Stated up front rather than buried:

- **AI evaluators, not a human coder (A3).** Both evaluators were very likely trained on the corpus, and the author, who holds the hypotheses, chose and configured them. AI repeatability is not human reliability or validity.
- **Post-exposure scoring amendments.** A7, A8, and A10 were each decided after some outputs were seen, though before any score comparison. Each is labelled with what had been seen.
- **One coder** (original plan), who selected the specimens, wrote the probes, and holds the hypotheses. Closed-form probes and a delayed re-code constrain that; they do not eliminate it. A second coder on a 20% sample is the single largest available credibility improvement and is not currently secured.
- **No blinding to arm is claimed.** The manipulation is visible in the artifact — a step component versus a prose paragraph *is* the treatment. Procedures that would falsely imply blinding are not used.
- **Implicit variants are constructed, not found.** They show what happens to one specific kind of under-marking: structure demoted to competent prose. Not to all bad documentation.
- **Forced-choice probes measure endorsement of a wrong relation**, which may run higher than spontaneous error. The comparison across stages and arms is symmetric, which is what the hypothesis needs, but the absolute rate should not be read as an error rate in the wild.
- **The corpus is in the training data** of any model used in phase 2. Phase 1 is immune by construction. Phase 2 treats contamination as a measured condition and names the residual confound rather than claiming it away.
- **Sample size supports description, not inference** to any general population of documentation.

## Open decisions

- ~~Repository license.~~ **Settled:** code is MIT, study data and instruments are CC BY 4.0, and corpus specimens — including the derived implicit variants, and corpus text reproduced inside pipeline artifacts — remain under Astro's own MIT terms with attribution. Nothing here is more restrictive than the documentation it studies.
- Which specific models phase 2 runs against, beyond the design's floor of three models across two vendors.
- Whether the server-mediated retrieval annex is run at all. It is observational, explicit-arm only, and carries no hypothesis — it can be dropped without affecting any result.
- Whether a second coder can be secured before phase 1 coding begins.

## Related

This experiment supports a five-part blog series on documentation, semiotics, and delivery pipelines. The design document, its version history, and the research base that produced it are maintained with the series planning material until registration, at which point `DESIGN.md` here becomes the frozen authoritative copy.

A deferred follow-on study — testing whether explicit marking matters more when a reader cannot fall back on the product's own interface and behavior — is described under *Future work* in the design. It needs its own apparatus and its own design document, but it needs sandboxing and tool gating that Inspect already provides, so it is expected to extend this harness rather than replace it. Its machine-checked outcomes would also remove the single-coder limitation this study can only mitigate.
