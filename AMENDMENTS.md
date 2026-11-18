# Amendments

## A10 — 2026-11-18 (post-L2, M1-AI coverage gate: malformed answers; decided after partial exposure)

**Change:** an assignment whose retained answer cannot be parsed by the frozen parser is documented unscorable under A8. That is status `malformed_json`: the answer is not one JSON object of strings, optionally inside a single enclosing ```` ```json ```` fence. Such an assignment is listed with its reason ("no usable answer after 1 attempt(s): malformed_json"), like the structurally invalid answers A8 already excuses. Implemented by adding `malformed_json` to `analysis.NEVER_EVALUABLE`. Adopted by the maintainer on 2026-11-18.

- **Unchanged:** the parser stays as frozen, with no lenient extraction of JSON from surrounding prose. Malformed answers are not retried, because non-transport outcomes are final. They are never scored.
- **Scope:** the rule applies to both evaluator configurations.
  - GLM-5.3-Flash: its ledger has no `malformed_json` status, so its gate, coverage, and kappa are unchanged.
  - Claude Sonnet 5.5 (A9) first pass: 5 of 1,832 assignments are excused. Each answer is an explanatory paragraph followed by a fenced JSON object, which the parser rejects with "Expecting value: line 1 column 1".
    - `AI-9f3a2e3d01e814a0024b-p1`
    - `AI-1bddf8a02624d0782951-p1`
    - `AI-fcfc353071500c90ecb0-p1`
    - `AI-090ee4e4c2e1e14fdb12-p1`
    - `AI-7a1c998ed7d5b27fb538-p1`
  - Claude repeat pass: no malformed answers.

**Rationale:** A8 excuses answers that are structurally invalid, so that 0.3% unscorable assignments do not block every finding. A malformed answer is the same kind of failure one step earlier: the answer was never usable as a protocol response. A8 omits it only because the GLM run never produced one. Without this rule, 5 of 1,832 (0.3%) would block all substantive A9 findings.

Alternatives considered:

- **Report the replication as blocked.** This is the protocol's fallback, but it would discard 1,827 scorable assignments over a formatting failure.
- **Parse leniently, taking the JSON out of the prose.** This would recover the 5 answers, but only by changing the frozen parser after seeing the outputs. Exclusion uses none of the answers' content.
- **Retry the 5.** This would contradict the rule that non-transport outcomes are final, and would select toward a result.

**Results seen?** Partially. All GLM results, the quote diagnostics, and the quote audit had been seen (see A9). For the Claude run, decided after both passes were collected. The author had seen:

- outcome counts by status (first pass: 1,297 recorded, 530 strict-invalid, 5 malformed; repeat: 241 recorded, 126 strict-invalid);
- the strict failure messages;
- for the 5 malformed answers, their stop reason, content block types, lengths, and first and last few characters.

No score, score distribution, A7 rescoring, kappa, or arm or stage comparison had been computed or viewed. The rule was fixed before any of them.

## A9 — 2026-11-18 (post-L2, second M1-AI evaluator on Claude; results seen)

**Change:** adds a second, separately stored M1-AI evaluator configuration and runs the locked first pass and repeat pass through it as an exploratory replication. The GLM-5.3-Flash records and their analysis are unchanged and stay the pre-specified M1-AI result.

- **Configuration** (`batch_runner.configuration_record`, transport `anthropic-batch-runner-1`, introduced in commit `61551ab5`):
  - Provider and model: Anthropic, `claude-sonnet-5-5`, through the Message Batches API.
  - Thinking: adaptive, the API default; nothing is sent.
  - Effort: `high`, the model's default and the setting piloted (maintainer decision).
  - Output cap: 32,000 tokens, the same as the OpenCode run.
  - Sampling: temperature and top-p are left at the provider default, because the model rejects non-default values. Seed and weights are unknown.
  - No tools and no fallback model.
  - Prompts: the system prompt is the pinned `AGENT_PROMPT` (sha256 `a1bde99e…`). The user message is `packet_text(packet)` verbatim, which carries the frozen evaluator instruction (sha256 `b5e514b8…`).
- **Unchanged:** the packets (`artifacts/assignments/packets.jsonl` and `repeat_packets.jsonl`, same opaque IDs, option orders and packet hashes), the locked 367-assignment repeat sample, A7 scoring (primary) with strict scores alongside, and the A8 gate (kappa at least 0.6, coverage reported, exclusions listed).
- **Isolation:** each assignment is one stateless request with a single user message, no tools and no prior turns. That replaces the OpenCode preflight and session-export checks. The evidence kept for every attempt:
  - the exact request body (`request.json`);
  - the response, which must come from the configured model, end with `stop_reason: end_turn`, and contain only text and thinking blocks;
  - the message ID, which stands in for the session ID.

  Blinding is unchanged: the artifact text can still reveal the arm.
- **Retries:** expired, canceled, and transient server-error results are resubmitted, at most 2 attempts. All other outcomes are final, as in the OpenCode runner.
- **Refusals:** a response that ends in `stop_reason: refusal` is recorded with status `refusal`, is final, and is never retried. Such an assignment is documented unscorable under A8 (`analysis.NEVER_EVALUABLE`), listed with its reason, so a refusal does not block the gate (maintainer decision). No OpenCode record has this status, so the GLM gate is unchanged.
- **Storage:** records go to `coding/claude-sonnet-5-5/` in the runner layout; the runner refuses `coding/`. A7 rescoring writes into the same directory (`make m1-ai-batch-rescore`), and analysis writes `analysis/m1_ai_a7_claude-sonnet-5-5/` and `analysis/m1_ai_strict_claude-sonnet-5-5/` (`make m1-ai-batch-analyze`). `rescore_a7.py` now labels these rows `anthropic-batch:<model>`; OpenCode rows keep `opencode:<provider>/<model>` (maintainer decision).
- **Pre-specified replication comparison**, fixed here before any Claude answer is seen:
  - The pre-specified tables are produced unchanged for the Claude records.
  - One comparison is added: for each stage A1–A4, the sign of the pooled explicit-minus-implicit A7 mean gap under each evaluator, and whether the signs agree. The same is reported for the correctness rate (score 2–3 against 0–1).
  - Evaluators are never pooled, and disagreements are reported, not reconciled.
  - Implemented as `replication.py` (`make m1-ai-replication`, output `analysis/replication_claude-sonnet-5-5/`). A side whose gate blocks substantive findings is reported as blocked and not compared.
  - Everything else is exploratory.

**Rationale:** the pre-specified M1-AI results (negative gaps at every stage, carried almost entirely by the 3-versus-2 support distinction) come from one evaluator. A second model family tests whether that pattern belongs to GLM-5.3-Flash or to the artifacts. On the maintainer's $220 budget, Sonnet 5.5 through the Batch API is the only Claude configuration that covers both passes. A free token count measured 121.38M input tokens. A 19-request paid pilot averaged 177 output tokens, which projects to about $123 for both passes (runlog, 2026-11-18). Opus 5.5 would cost about $247.

**Results seen?** Yes, for the study overall. The author, and the AI assistant drafting this amendment, have seen:

- all pre-specified GLM M1-AI results;
- the unplanned quote diagnostics;
- the unplanned quote audit.

The direction of the expected pattern is therefore known. For the Claude configuration itself, only token counts and the pilot's usage, stop reasons, and content block types were seen. No Claude answer or score has been read. The replication is exploratory and model-conditioned under A3, and cannot be read as confirmatory.

**Approval still required (A3):** a separate maintainer approval of the paid run, with a budget (projected about $123) and a call cap (`MAX_INVOCATIONS`).

## A8 — 2026-09-24 (post-L2, M1-AI coverage gate; decided after partial exposure)

**Change:** the M1-AI analysis gate no longer requires every locked assignment to have a record. An assignment may be missing only if it is documented as unscorable by evidence: (a) its retained answer remains structurally invalid under A7 (opaque-ID mismatch, wrong fields, unknown option or support), or (b) all its allowed attempts ended in transport failure (or it was oversize). Any other missing first-pass or repeat assignment still blocks substantive findings. Repeatability is unweighted Cohen's kappa over the locked seed-selected repeat sample minus documented-unscorable assignments; kappa below 0.6 or undefined still blocks. Reports state coverage and list every excused assignment with its reason. Both A7 (primary) and strict analyses use the same documented list, so the strict version still fails wherever quotes are unverifiable.

**First-pass effect:** 5 of 1,832 assignments are documented unscorable (coverage 1,827/1,832): three opaque-ID mismatches (S09-O2-at-024636 A2 explicit; S06-R2-001 A3 explicit; S06-O1-at-002202 A3 explicit), one field mismatch (S11-O2-at-004129 A3 implicit), and one double timeout (S07-O1-at-001725 A1 implicit).

**Rationale:** without this, 0.3% structurally unscorable assignments would block every substantive M1-AI finding. The maintainer chose to report coverage and list the exclusions rather than accept the block or rerun selected assignments.

**Results seen?** Partially, as for A7: first-pass counts, the unscorable list, and A7 flag counts were known; no score distributions, comparisons, or repeatability had been computed. Decided on 2026-09-24 before the repeat pass.

## A7 — 2026-09-24 (post-L2, M1-AI scoring; decided after partial exposure)

**Change:** quote verification and invalid-response handling for M1-AI (amends the frozen protocol `m1-ai-1`; scoring version `m1-ai-1+A7`). A quote now counts as verified if, after decoding HTML entities, removing HTML/JSX tags, reading A2 snapshot nodes as their names and values (dropping `/url:` lines; applied only to multi-line snapshots), and folding case, quote marks, dashes, and whitespace as in `locators.fold`, it occurs in the artifact's readable text; a quote of `…`-joined fragments counts if every fragment (at least 12 folded characters) occurs in order. Scoring is by the chosen option: foil 0; absence option 1; correct option 3 with explicit support and a verified quote (exact or normalized), otherwise 2. Departures from the strict rules are flagged (`quote_verified_after_normalization`, `explicit_quote_unverified`, `absence_with_support_or_quote`, `substantive_choice_with_absent_support`, `inferred_without_rationale`). Opaque-ID mismatches, wrong fields, and unknown options or support values remain invalid. A7 scores are derived from retained answers (`make rescore-a7` → `coding/m1_ai_a7_records/`, `coding/m1_ai_a7.csv`) without new evaluator calls; the strict append-only records are untouched, each A7 row keeps its strict score or strict error, and analysis reports A7 (primary) and strict side by side. The prompt, packets, options, and evaluator configuration are unchanged, and the repeat pass is scored the same way.

**Rationale:** the strict rule required a byte-exact substring of the artifact. Stage transformations (entities and tags in A1 HTML, node syntax in A2 snapshots, typographic folding) made most faithful quotations fail, and the frozen policy then discarded the whole answer, so first-pass coverage could never be complete. The maintainer chose readable-text normalization with fragments, and scoring unverified quotes by option with flags, on 2026-09-24.

**Results seen?** Partially. Decided after the first pass: the author had seen rejection messages and the evidence strings of rejected answers (categorized: 363 not found after folding, 147 ellipsis-joined, 81 differing only in quotes/dashes/markup/whitespace), and three retry outcomes. No score distributions, arm or stage comparisons, or analysis outputs had been computed or viewed. The rule was fixed before any rescoring.

## A6 — 2026-09-24 (post-L2, mechanical anchor repair)

**Change:** mechanical anchor repair after L2 (P7 task 3). In the first complete generation run, resolution failed for one instance only, S10-O2-at-013229, in both arms: its host ended on the code line `npx nightwatch test/index.js`, and the end locator (`est/index.js`) also matched the rendered code-frame title `src/test/index.js` of a later block (Expressive Code renders a fence's `title` as text; the A0 projection omits fence info lines). The host now ends at the next prose sentence ("Additionally, you can run the tests against a specific browser using the"), in both arms. Only that instance's two host passages and its review note changed; its probe, answer, foils, anchor, and gate evidence are unchanged, and the evidence quote remains inside the host. `locators.py` is unchanged; all other 228 retained instances had resolved.

**Rationale:** the registered procedure treats an anchor that fails to resolve as an anchor defect, repaired mechanically and results-not-seen, with resolution re-run against the archived artifacts rather than the build.

**Results seen?** No. To diagnose, the author read only the two end-locator matches in the S10 A3 text (about 50 characters of context each). No packets or evaluations existed. The archived A1-A4 (6,313 A1 pages per arm; 238 A4 chunks) passed integrity checks and are reused unchanged via `make artifacts-resume`.

## A5 — 2026-09-23 (post-L2, mechanical)

**Change:** mechanical repair of the implicit arm after L2. De-marking rule D3 wrote an aside's force phrase and its first body line on one line; when the body began with block HTML, S03 (`recipes/sharing-state-islands.mdx`) became `FAQ: <details>` and `Note: <details>`, which MDX parses as unclosed inline JSX, so the implicit arm could not build. D3 now puts the phrase in its own paragraph before a body that opens with an HTML/JSX element (`FAQ:` / blank line / `<details>`). `make demark` regenerated the implicit arm: only those two S03 asides changed (one line break each); all 24 corpus files parse with the pinned `@mdx-js/mdx` 3.1.1. Recompiling the instrument changed only three S03 implicit host passages (whitespace-identical: S03-R2-005, S03-R3-001, S03-R3-004) and one note's implicit offsets (S03-O2-at-002497); occurrence-decision offsets for S03 shifted by 1-2 characters. Probes, answers, foils, exclusions, gate evidence, templates, and the seed are unchanged.

**Rationale:** the build failure made the locked implicit S03 unbuildable. Template wording and the rule's meaning (the aside becomes prose carrying the same force) are unchanged; only a line break moves. Excluding S03 would have removed 12 retained instances and changed the specimen list. Maintainer approved on 2026-09-23.

**Results seen?** No. The first generation run built the explicit A1 tree before the implicit build failed; that partial output (9,064 files, manifest sha256 `3253f8ef6b96e947ba575ec086b910043982db9595c6e521d4345e0f24fbd78b`) was never opened and was deleted so the artifact set is generated once, from one run. No A2-A4, packets, or evaluations existed.

## A4 — 2026-09-23

**Change:** `DESIGN.md` v0.8→v0.9 replaces the A3 extraction target `<article>` with exactly one `.sl-markdown-content`. No fallback to `article`, `main`, or `body`; zero or multiple matches fail. All text inside the container remains, including generated in-content navigation, subject to pilot assessment before L2.

**Rationale:** the pinned corpus template uses this content container rather than `<article>`. The maintainer explicitly approved the amendment and disposable-pilot verification in this session.

**Results seen?** No new study downstream artifacts or results inspected. Template inspection, synthetic tests, and the historical logs disclosed under A3 informed the correction; production-pilot verification was pending at approval.

## Earlier Amendments

| Date       | Change                                                                                                                                                                                                                                                                                                                                             | Rationale                                                                                                                                                                                                                                                                                                                                  | Results seen?                                                                                                                                                                                                       |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-09-23 | **A3** — `DESIGN.md` v0.7→v0.8: authorized AI authoring and the both-arms gate, AI-assisted M2, and a separate exploratory M1-AI measure. Model-free and human reliability claims are withdrawn for this execution. Fresh-context AI repeatability replaces the human seven-day re-code; the evaluation protocol must be frozen before evaluation. | Maintainer explicitly authorized AI assistance after disclosure that it changes the registered methodology. Human M1a is not synthesized. Engineering gates, the occurrence-based unit, L2-before-artifacts, append-only records, and evidence requirements remain binding. Paid runs and expanded Phase 2 work require separate approval. | No study downstream results inspected in this authorization session; historical pilot findings and the runlog's previously recorded pre-L2 incidents were read. Historical artifact absence remains to be verified. |
| 2026-08-02 | **A1** — Added de-marking rule D8 to `DESIGN.md` (v0.6→v0.7): prerequisite-heading blocks lose their heading; content stays in place, introduced by a template sentence asserting the precondition relation.                                                                                                                                       | The corpus's dominant R4 idiom ("Prerequisites" headings, 48/417 en pages, per the component report) had no applicable de-marking rule after D6 was cut at 0.3; the manipulated R4 cell could not approach its ≥20 minimum. D8 avoids D6's relocation flaw — nothing moves. Maintainer-approved.                                           | No                                                                                                                                                                                                                  |
| 2026-08-02 | **A2** — Repaired stale D4 wording in `DESIGN.md` → _The marking manipulation_: two paragraphs still prescribed the 0.3 paraphrase mapping (`MUST` → "needs to"), contradicting the 0.4 lowercasing rule and ADR-0001.                                                                                                                             | Internal inconsistency in the registered text, found while drafting A1. Rule table and changelog were already correct; no study behavior changes.                                                                                                                                                                                          | No                                                                                                                                                                                                                  |
