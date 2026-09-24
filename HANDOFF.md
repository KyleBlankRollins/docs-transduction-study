# Study Readiness Handoff

As of 2026-09-23. This is an engineering handoff, not an amendment, instrument
lock, or authorization to launch evaluations. Continue in this repository; no
previous chat history is required. Verify live files before editing because the
working tree contains uncommitted work.

## Mission and Authority

Make the amended AI-assisted study ready to run, including the OpenCode runner,
instrument preparation, artifact orchestration, and downstream analysis code.
Implement and test the work, rather than returning another general plan. Use
small, local reads and focused tests to conserve the maintainer's agent credits.
Do not rerun the expensive full-site pilot merely to rediscover verified facts.

The maintainer authorized AI probe authoring, A0 gating, historical-source
verification, and AI-assisted M2 inspection. Historical HUMAN assignments are
superseded only where amendment A3 permits. They also authorized fresh isolated
evaluator sessions and selected **GLM-5.3-Flash**. They want routine engineering
decisions handled autonomously; ask only about consequential unresolved choices.

Read these in order, using the relevant sections rather than the entire history:

1. [DESIGN.md](DESIGN.md): Status, amendment A3, Probes, Pipeline, Analysis plan.
2. [coding/AI_PROTOCOL.md](coding/AI_PROTOCOL.md): current scoring and isolation contract.
3. [phases/p06-probes-and-lock.md](phases/p06-probes-and-lock.md): current status and L2 gate.
4. [runlog.md](runlog.md): newest entries; older pending statements are superseded.
5. [AMENDMENTS.md](AMENDMENTS.md) and relevant [decisions/README.md](decisions/README.md).

DESIGN v0.9 and amendments A1-A4 govern. The implementation plan and historical
phase checkmarks are not proof of completion and sometimes describe obsolete
human/model-free workflows. This handoff does not override the design.

## Non-Negotiable Boundaries

- L1 exists: 2026-08-02, commit `75667a9a494b076e79e9f5aba5bd0dc932d890a1`.
  **L2 does not exist.** No study probes, study evaluations, or commits were
  produced during this takeover. Check current instrument contents directly.
- Do not generate or inspect study A1-A5 artifacts before a real L2. The named
  non-sample pilot exception permits disposable engineering checks. Full-site
  pilot builds transiently generated non-pilot output, which was not inspected
  as prose or retained. Preserve that distinction in reporting.
- Human M1a must not be synthesized. Automated judgments are exploratory
  **M1-AI**, separate from human records and M1b. Human/model-free reliability,
  model independence, and training-data immunity claims do not apply.
- Each evaluator sees only its packet, never A0, answer keys, authoring history,
  prior answers, other assignments, or repository context. Opaque IDs alone do
  not establish blindness. The authoring agent must not evaluate study packets
  in its own contaminated conversation.
- Paid/provider-quota-consuming tests and full runs need separate approval.
  Existing credentials and model selection are not an unlimited run budget.
  Ask once with a concrete bounded smoke-test proposal after offline tests pass.
- Do not commit, branch, publish, run expanded Phase 2, or take L2 without
  explicit authorization. Prepare a concise L2 approval package when ready.
- Preserve existing user changes and [coding/seed](coding/seed). Do not use
  blanket staging, reset the worktree, regenerate the seed, or expose secrets.
- After L2, instrument changes require amendments. Report genuine gate failures;
  never recode, exclude, shorten artifacts, or adjust protocols toward a result.

## Verified Baseline

- Python 3.14.6 via `uv` and `.venv`; Node v22.19.0; pnpm 11.24.0.
  Playwright 1.62.0; BeautifulSoup 4.15.0. Record actual versions at execution.
- Last full `make check`: **92 pytest and 44 Vitest tests passed**, plus ruff,
  mypy, and TypeScript checks. These are historical results, not new validation.
- Production pilot completed both full arm builds plus a clean explicit repeat.
  All **6,313 HTML paths matched byte-for-byte** between explicit builds.
- A2 used compiled HTML with working assets, loopback HTTP, default page state,
  no interaction, and two identical native YAML snapshots per arm.
- A3 strictly selects exactly one `.sl-markdown-content`; no fallback or selective
  cleanup. A4 uses lossless **1,500-character, zero-overlap** slices.
- Pilot extraction: explicit 9,565 characters / 7 chunks; implicit 10,635 / 8.
  Generated heading/code labels remain: 5.71% / 4.85% overall; maximum chunk
  fractions 10.8% / 8.6%. Do not claim chrome-free extraction or demonstrated
  unmarked sequence corruption. Tab labels carry relational evidence.
- A disposable tool-free Copilot evaluator dry run validated plumbing only.
  Its underlying model/version was unknown. The repeat sample was too small
  for defined kappa, and the gate correctly failed. It was not a GLM test.
- Pilot artifacts, probes, records, temporary inputs, and three full build trees
  were disposed of; absence was verified and logged. No jobs remain running.

## Work Order and Acceptance Criteria

### 1. Wire the Isolated OpenCode Runner

Extend the existing [src/docs_transduction_study/coding_ai.py](src/docs_transduction_study/coding_ai.py)
core; do not replace it or route AI work through the legacy human harness.
Reuse [tests/test_coding_ai.py](tests/test_coding_ai.py) and add a focused runner
test module only if needed. A separate runner module is reasonable.

Local OpenCode is installed at `/Users/kylerollins/.opencode/bin/opencode`, version
**1.18.32**. Its catalog lists:

| Provider    | Exact CLI model ID                    | Status                              |
| ----------- | ------------------------------------- | ----------------------------------- |
| OpenCode Go | `opencode-go/glm-5.3-flash`           | Recommended study route, not frozen |
| ClinePass   | `cline-pass/cline-pass/glm-5.3-flash` | Available alternative, not tested   |

Authentication is already configured. Catalog listing did not test authenticated
inference. Do not read or print auth files, copy keys into this repo, or dump
resolved configurations containing credentials. Use the existing secret store.
Never silently fail over providers: the same model label may have different
serving behavior. The alias also does not pin model weights.

Verified CLI capabilities: `run`, `--model`, `--agent`, `--format json`, `--dir`,
`--title`, `--pure`, and session export. JSON format is an **event stream**, not
a guarantee that the answer obeys the scorer's JSON schema. Never use resume,
continue, fork, auto-approval, or sharing for evaluator assignments.

Implementation requirements:

- Run from a clean temporary workspace outside the repository, with a fresh
  session for every assignment and repeat. Deny all tools, including MCP tools.
- Explicitly exclude inherited global/project instructions, skills, plugins,
  MCP connections, and history. A temporary cwd and `--pure` alone are not proof:
  inspect effective configuration and session input without exposing secrets.
  OpenCode merges configuration; empty objects may not remove inherited entries.
- Pin provider/model, CLI version, evaluator prompt, available generation
  settings, and configuration hash. Record unavailable settings as unknown.
  Update the protocol's old Copilot-specific invocation instructions when the
  OpenCode transport is verified; keep historical pilot provenance intact.
- Disable sharing and unwanted compaction/truncation. Check auxiliary title,
  summary, and compaction model calls; they can add context changes and cost.
  Do not assume one CLI invocation equals one provider request.
- Supply only `prepare_packet`'s public packet. Keep its private scoring key
  outside the evaluator's accessible context. Reject oversize inputs explicitly.
- Retain raw events, actual session and provider/model metadata, exact packet,
  parsed response, usage if available, exit status, and failures. Detect tool
  events, wrong model, unexpected history, incomplete output, and malformed JSON.
- Connect successful responses to `score_response` and `record_response`.
  Keep a single writer; the existing JSON-then-CSV write can need reconciliation
  after a crash. Never overwrite or silently rerun a retained judgment.
- Add bounded timeouts, an explicit call budget, and failure recovery. No
  unbounded retries or automatic provider switching on quota exhaustion.
- Verify Go/ClinePass workload terms and quota behavior, including possible
  paid-balance fallback. Native OpenCode does not itself authorize bulk usage.

Start with mocked CLI event/export fixtures and synthetic packets: fresh
sessions, deny-all configuration, exact scoring, malformed/error/tool output,
timeouts, duplicates, crash recovery, and repeat consistency. Then request a
bounded disposable live smoke test, with a stated maximum invocation count and
possible auxiliary calls. Do not use study artifacts. Dispose of pilot material
and record aggregate verification before freezing the protocol.

Useful official references (verify against installed CLI, not memory):
[CLI](https://opencode.ai/docs/cli/), [agents](https://opencode.ai/docs/agents/),
[permissions](https://opencode.ai/docs/permissions/),
[Go](https://opencode.ai/docs/go/), [ClinePass](https://cline.bot/cline-pass/).
Copilot BYOK is possible but is not needed for this runner.

### 2. Finish the Occurrence-Based Instrument

The accepted [instruments/instances.csv](instruments/instances.csv) still has
560 rows: R1 32, R2 34, R3-D3 61, R3-D4 0, R4 9, O1 369, O2 55.
The R4 shortfall is disclosed and permitted as a recorded shortfall, not a
reason to manufacture rows or change the corpus casually.

The old O1/O2 extractor deduplicated expression strings rather than occurrences.
That extraction bug is repaired, but **migration and semantic review are not**.
Separate generated files under `build/` may be ignored/untracked:

- `build/occurrence-candidates.csv`: 567 candidates, 498 O1 and 69 O2.
- `build/occurrence-review/o1_review.csv` and `o2_review.csv`: all 567 paired
  across arms using source offsets and unchanged token alignment.
- These cover 477 legacy expressions: 424 accepted and 53 rejected first
  occurrences, plus 90 repeats. They are not 567 accepted study instances.

Use [src/docs_transduction_study/inventory.py](src/docs_transduction_study/inventory.py)
and [src/docs_transduction_study/review_o1_o2.py](src/docs_transduction_study/review_o1_o2.py).
Classify each occurrence from its local A0 context, retain reasons and explicit
old-to-new ID provenance, and migrate only reviewed decisions. Repeats do not
inherit acceptance automatically. Do not treat regex fragments/code matches or
the old mechanical classifier as semantic evidence.

Assign genuinely minimal answerable host passages and short per-arm anchors.
Existing broad hosts are not automatically suitable. Verify unique occurrence
resolution in both A0 arms, not merely that the same phrase occurs somewhere.
Use structured CSV parsing. Update dependent review/probe references atomically.
Acceptance: complete reviewed inventory, traceable decisions, both-arm A0 anchor
checks, accurate counts, and focused occurrence regressions.

### 3. Author, Gate, and Prepare L2

Follow [phases/p06-probes-and-lock.md](phases/p06-probes-and-lock.md) under A3.
Author one closed-form probe per retained instance, with one or two relational
foils and the standard absence option added at presentation. Avoid distinctive
source strings. Answer each probe independently from both A0 variants and retain
evidence for the gate. Record failures with reason, failed arm, and date before
lock; do not silently discard them.

Verify every designated version-change answer against actual pre-change source
or a changelog, retaining the SHA/URL and evidence. Do not invent a historical
answer to populate the subset. Check linter treatment of exclusions against the
design: accepted probes must equal instances minus valid exclusions, with no
duplicate, missing, or foreign IDs. A green linter is not semantic gate evidence.

Preserve the existing seed. Freeze normalization, templates, instrument, and the
verified AI protocol/configuration. Confirm pilot disposal and no retained study
artifacts. Prepare the actual six-file L2 lock set:

- [corpus/specimens.csv](corpus/specimens.csv)
- [instruments/instances.csv](instruments/instances.csv)
- [instruments/probes.csv](instruments/probes.csv)
- [instruments/gate_exclusions.csv](instruments/gate_exclusions.csv)
- [pipeline/demark/templates.json](pipeline/demark/templates.json)
- [coding/seed](coding/seed)

Ask for approval before the two-commit L2 operation. The first commit locks the
instrument; the following commit records its real SHA/date in DESIGN and the
runlog. Verify the commit object and locked file contents, not just a date or
plausible SHA string. Never claim readiness to generate artifacts while L2 is blank.

### 4. Complete P7 Artifact and Assignment Plumbing

Implement and test before L2 using synthetic fixtures or the named pilot only;
execute on study specimens only after authorized L2.

Use [phases/p07-artifacts.md](phases/p07-artifacts.md) and
[src/docs_transduction_study/stages/a1_build.py](src/docs_transduction_study/stages/a1_build.py).
The current `make artifacts` omits A2. Non-pilot verification is less complete
than the validated pilot path. Complete one fail-closed A1-A4 driver that:

- Validates the actual L2 commit and frozen inputs before any study generation.
- Builds both complete pinned trees with the identical deterministic ad overlay;
  missing overlays must fail, not warn. Preserve compiled assets through A2.
- Checks matching routes/page sets and determinism, captures stable default-state
  A2 via `body.aria_snapshot()`, and records versions, hashes, and configuration.
  Playwright 1.62.0 removed `Page.accessibility`; do not restore that API.
- Uses strict A3 extraction and lossless A4 slicing with complete per-arm manifests.
- Resolves anchors/hosts deterministically, fails on ambiguity or missing data,
  and emits per-arm chunk selection and `spans_chunks` without editing instruments.
- Packages exactly eight assignments per eligible instance: two arms times
  A1-A4. A1 is complete HTML, A2 complete snapshot, A3 complete extracted text,
  A4 exactly the chunk containing that arm's host-passage **start**.

Preserve page-relative routes, not basenames. Never use explicit-arm chunk IDs
for implicit assignments, pick a more answerable neighboring chunk, or truncate
whole-page input to fit a model context. Missing evidence in default-hidden A2
content is not automatically an anchor defect; distinguish structural absence
from broken locating logic and escalate unresolved design conflicts.

Freeze deterministic assignment order, randomized options, opaque IDs, and the
seed-selected repeat sample before responses. Keep keys/mappings out of evaluator
inputs and satisfy remaining mapping-at-rest requirements; reversible naming is
not encryption or blindness. A0 MDX hosts may not survive rendering literally:
test normalization/mapping now, never introduce fuzzy semantic fallback later.

### 5. Make Coding, M2, and Analysis Executable

Read [phases/p08-coding.md](phases/p08-coding.md),
[phases/p09-redundancy.md](phases/p09-redundancy.md), and
[phases/p10-analysis.md](phases/p10-analysis.md) through amendment A3.

- Keep AI records in `coding/m1_ai.csv`, human records untouched. Full first-pass
  coverage and fresh-session repeats use identical packets/configuration.
- Repeat exactly the seed-selected 20% of assignments, rounded up. Unweighted
  Cohen's kappa below 0.6, undefined kappa, incomplete records, or unverified
  isolation blocks substantive findings. Do not import the human seven-day delay
  into M1-AI or report AI repeatability as human reliability/validity.
- Implement analysis targets (currently stubs) against synthetic data first.
  Report counts, full score distributions, means and arm gaps by stage, pooled
  and per specimen; H2 descriptive O1/O2 comparisons; R3 D3/D4 separately; H3
  corrupted/absent at A4 with per-arm span flags. Handle empty cells and zero
  denominators explicitly. Label H1-H3 output exploratory and model-conditioned.
- M2 needs observed docs/CLI/runtime evidence, not assumptions from prose.
  Capture actual commands and bounded disposable runtime checks; label the
  inventory AI-assisted. Unknown/unobserved evidence is not a confirmed absence.
- Keep unplanned analyses separately labeled. Test that failure gates prevent
  substantive reports while allowing transparent engineering/failure reports.
- [phases/p11-phase2-study.md](phases/p11-phase2-study.md) remains separately
  gated. One GLM evaluator does not satisfy M1b's multi-model/multi-vendor design.
  Do not launch A5, closed-book covariates, expanded Phase 2, or publication.

Once N eligible instances is known, quote **8N first-pass assignments plus
ceil(0.2 \* 8N) repeats**, before retries/auxiliary calls. The old 560-row count
would imply 5,376 evaluations, but migration/exclusions will change N. Present
the final volume, input/context limits, quota policy, and bounded cost/run plan
for approval; no full evaluation launch is authorized yet.

## Local Code Hazards

- [src/docs_transduction_study/coding.py](src/docs_transduction_study/coding.py)
  is the historical human harness, not the AI runner. Known problems include
  explicit-chunk reuse, generic options, and weak mapping/order handling.
  `make coding-setup` and `make code` invoke it; do not use them for M1-AI.
- [src/docs_transduction_study/assign_anchors.py](src/docs_transduction_study/assign_anchors.py)
  and [src/docs_transduction_study/merge_classification.py](src/docs_transduction_study/merge_classification.py)
  retain first-match/fuzzy or broad-host behavior. Do not blindly rerun them.
- [src/docs_transduction_study/anchors.py](src/docs_transduction_study/anchors.py)
  has repaired raw-coordinate normalization, full-route lookup, host-start
  selection, per-arm spans, and separate fail-closed assignment output. Preserve it.
- [src/docs_transduction_study/classify_o1_o2.py](src/docs_transduction_study/classify_o1_o2.py)
  uses heuristics; some old accepted rows retain stale rejection reasons.
- `make inventory` intentionally refuses unsafe legacy/positional merging.
  Do not bypass the safeguard to make the command green.
- In source masking, frontmatter must be anchored at document start (`\A`),
  not multiline `^---`, which can swallow embedded Astro examples. Pairing uses
  token SequenceMatcher; character-level alignment was prohibitively slow.
- Non-pilot A1 currently checks a lock date, not a fully verified lock commit.
  Its older determinism/extraction helpers need integration, not assumed parity
  with the tested pilot helper. See [tests/test_p5.py](tests/test_p5.py).

## Validation and Completion

Use the existing environment; inspect [pyproject.toml](pyproject.toml) and
[Makefile](Makefile) for current entry points. `rg` was unavailable in this shell;
use editor search or `grep` instead of repeatedly trying it.

```sh
uv run pytest tests/test_coding_ai.py
uv run pytest tests/test_inventory_occurrences.py
uv run pytest tests/test_lint_probes.py tests/test_p6_seed.py
uv run pytest tests/test_p5.py
make anchors-a0
make inventory-counts
make lint-probes
make check
```

Run only the focused checks relevant to each edit, then the complete gate at
readiness. Instrument checks may legitimately fail until review/authoring is
complete; do not weaken them. Do not run `make artifacts`, `make pilot`, or
instrument-writing targets just to inspect their behavior.

Maintain dated runlog entries and update the current status in phase docs and
the AI protocol. Preserve historical evidence; never replace it with a claim
that all tests or gates passed if only one slice was checked.

Deliver a short final readiness report containing:

- Implemented commands and exact offline/live validations, with unresolved gates.
- Final instrument counts, exclusions, source-verification evidence, and seed hash.
- Frozen evaluator configuration and isolation evidence, or the precise blocker.
- L2 approval package or actual authorized/verified lock SHA.
- A deterministic dry-run assignment manifest and call-volume estimate.
- Exact post-lock launch/resume commands, required approvals, and failure behavior.

The target is a tested, auditable workflow waiting only on explicit lock/run
approvals, not a prematurely launched study or a fabricated completed result.
