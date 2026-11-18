# Runlog

Entries are reverse-chronological. This record begins before registration; deviations and lock events are added as they occur.

## 2026-11-18 — Amendment A9 adopted (second M1-AI evaluator on Claude); no run yet

The maintainer accepted the three open choices in the A9 draft: effort `high`,
refusals documented unscorable under A8, and a corrected evaluator label for
batch records. Implemented: `batch_runner.py` records refusals with status
`refusal`; `analysis.NEVER_EVALUABLE` now includes `refusal`; `rescore_a7.py`
labels batch rows `anthropic-batch:<model>` (OpenCode labels unchanged); the
pre-specified replication comparison is `replication.py`; Makefile targets
`m1-ai-batch-rescore`, `m1-ai-batch-analyze`, `m1-ai-replication`. The GLM gate
was re-run after the change and is unchanged (coverage 1,827/1,832, 5 excused,
kappa 0.668 over 365 pairs; no GLM ledger entry has status `refusal`). The
adopting commit's SHA goes in `DESIGN.md` frontmatter in a follow-up commit, as
for A5-A8. No Claude answer or
score has been seen; the paid run awaits a separate budget approval (A3).

## 2026-11-18 — UNPLANNED Claude token count and paid output-token pilot (Sonnet 5.5, batch)

Maintainer-requested, to cost a possible re-run of M1-AI on Claude. Not an
evaluation: no answer keys were loaded and no answers or scores were read.

**Token count (free endpoint, no inference).** All 2,199 packets were sent
exactly as the runner sends them (system `AGENT_PROMPT`, user
`packet_text(packet)`) to `count_tokens` under the maintainer's `ant` profile:
121.38M input tokens (first pass 100.93M, repeat 20.45M; median 10.5K, max
332K; 204 packets over 200K). Opus 5.5 counts matched Sonnet 5.5 exactly on 40
packets.

**Pilot (paid, maintainer-approved).** 19 first-pass packets chosen at size
quantiles of those counts (729 to 216K tokens; the single 332K packet left out
for cost) were submitted with the draft `batch_runner.py` (commit `61551ab5`):
`claude-sonnet-5-5`, effort `high`, adaptive thinking, max 32,000 output
tokens, Message Batches API (batch `msgbatch_01GnZdkHjjkFDWvtfgmeriQA`). Output
went to a scratch directory outside the repository and was not retained; only
usage, stop reasons, and content block types were read. All 19 succeeded with
`end_turn`; 854,236 input tokens (equal to the counts), 3,357 output tokens
(mean 177, max 362); one response carried a thinking block. Cost about $0.87.
No study records were created, so these 19 assignments remain unevaluated by
this configuration.

**Projection (batch prices):** full first pass plus repeat about $123 on Sonnet
5.5, about $247 on Opus 5.5. A full run still needs separate approval (A3) and
an amendment recording the new evaluator configuration.

## 2026-09-27 — UNPLANNED blinded quote audit completed (DeepSeek V4 Pro)

After the maintainer enabled Global regions, the audit resumed; a crash on an
interrupted attempt folder was fixed (next free attempt number, folder kept).
All 100 items recorded; 104 invocations in total (3 earlier region rejections, 1
interrupted call). Unblinded categories (Faithful / Paraphrase / Not supported /
Cannot tell): explicit 43 / 3 / 4 / 0; implicit 46 / 1 / 2 / 1 (n = 50 each).
By stage, explicit A1 22/1/0/0, A2 14/2/2/0, A3 6/0/1/0, A4 1/0/1/0; implicit A1
21/0/0/0, A2 18/0/1/1, A3 6/0/1/0, A4 1/1/0/0. Most quotes that A7 could not
verify were judged faithful in both arms, so the `explicit_quote_unverified`
flag mostly reflects verifier misses, slightly more often in the explicit arm.
Caveats: single AI auditor of unknown reliability; blinding partial; 50 items
per arm. Unplanned and exploratory; the pre-specified results are unchanged.

## 2026-09-27 — Quote auditor set back to DeepSeek V4 Pro (no calls)

After comparing options (Muse Spark rejected: Go docs state prompts and
completions may train future Meta models; DeepSeek V4 Flash likely shares the
Global-region requirement), the maintainer chose DeepSeek V4 Pro and will enable
Global regions in the workspace. Kimi K3 was never called. Audit calls wait for
confirmation that the setting is enabled.

## 2026-09-27 — Quote auditor switched to Kimi K3 (no calls yet)

Maintainer chose `opencode-go/kimi-k3` after DeepSeek V4 Pro required Global
regions. Kimi K3 is a different family from the GLM evaluator (1M context,
reasoning model) but does not accept a temperature setting, so the auditor runs
at the provider default (recorded as temperature not set). Offline preflight
passed. Catalog price is $3/M input and $15/M output, well above DeepSeek.

## 2026-09-27 — Quote audit stopped: DeepSeek on Go requires Global regions

The maintainer approved the audit with DeepSeek V4 Pro (cap 120). The first three
calls failed with HTTP 400 (not retryable): "This Go model requires Global
regions. Select Global in your workspace's Privacy settings to use it." The run
was stopped after 4 invocations (the fourth was interrupted); no auditor answer
exists. The rejections occurred upstream before inference, so billing is
unlikely but unverified. The runner and audit treated this as a retryable
transport failure and saved no error detail; both now stop the batch on any
provider error marked non-retryable (`provider_rejected`) and keep the error
text. The three failed items remain eligible for one retry. Awaiting a
maintainer decision on the workspace region setting or another auditor model.

## 2026-09-27 — UNPLANNED blinded quote audit prepared (no calls yet)

Maintainer chose an isolated AI auditor. `quote_audit.py` draws a seed-ranked,
stage-stratified sample of first-pass answers flagged
`explicit_quote_unverified` (50 per arm; 100 items, shuffled) and writes
`coding/quote_audit/packets.jsonl` (item ID, quote, the artifact's readable
text, four categories: Faithful, Paraphrase, Not supported, Cannot tell) and a
separate `key.jsonl`. Arm, stage, instance, and scores are withheld; blinding is
partial because page text can reveal the arm. Auditor: `opencode-go/deepseek-v4-pro`
(different model family from the evaluator), same isolation checks and
file-based output as the runner; offline preflight passed. Packets total 4.48
MB (median 27 KB, max 107 KB). The sample is fixed once drawn. Calls await a
separate budget approval.

## 2026-09-27 — UNPLANNED exploratory quote diagnostics (maintainer-requested)

After the pre-specified results were seen, the maintainer asked whether the
implicit arm's higher scores reflect quote verifiability rather than survival.
`exploratory.py` (first-pass A7 records) wrote
`analysis/exploratory/quote_diagnostics/`; it is not pre-specified and does not
replace the pre-specified tables.

**Correctness (score 2-3 versus 0-1), explicit vs implicit:** A1 0.996 vs 0.996;
A2 0.974 vs 0.987; A3 0.996 vs 0.996; A4 0.904 vs 0.886. Gaps: 0.000, -0.013,
0.000, +0.017. The pre-specified negative gaps therefore come almost entirely
from how correct answers were supported (3 versus 2), not from whether the
relation was answered correctly.

**Support of correct answers (explicit / implicit):** exact quote A1 28/41, A2
23/34, A3 132/146, A4 133/146; quote verified only after normalization A1
68/88, A2 86/93, A3 44/47, A4 28/31; unverifiable explicit quote A1 112/96, A2
90/91, A3 33/30, A4 10/7; support self-reported as inferred A1 20/2, A2 23/8,
A3 17/4, A4 36/19. The explicit arm has fewer quotable supports and more
self-reported inference at every stage. Plausible reading (not tested): the
implicit arm states each relation in a sentence ("These are alternatives — use
exactly one"), while the explicit arm carries it in structure (tabs, numbering,
callout type) that offers nothing to quote, so the rubric's "explicit support"
criterion favours prose statements.

## 2026-09-24 — Repeat pass, gate, and pre-specified M1-AI analysis (exploratory)

Repeat pass (maintainer-approved, cap 2,700): 367/367 attempted once, no
transport failures; 2,660 invocations in total. A7 rescoring: 2,194 records
(1,827 first pass, 367 repeats); 4 structurally invalid. Gate (A7, primary):
coverage 1,827/1,832 with 5 documented exclusions; unweighted kappa **0.668**
over 365 repeat pairs; substantive findings allowed. Strict gate: coverage
852/1,832, 975 first-pass and 225 repeat assignments missing; blocked, as
expected under the strict quote rule.

`make analyze` wrote `analysis/m1_ai_a7/` (H1 pooled and per specimen, H2 O1/O2,
R3 by device, H3 overall and by arm × spans_chunks) and
`analysis/m1_ai_strict/report.json` (failure report). All outputs are
exploratory, model-conditioned M1-AI (GLM-5.3-Flash via OpenCode Go), not M1a
or M1b, and scored under post-hoc amendments A7/A8 decided after partial
exposure. Pooled explicit-minus-implicit mean gaps: A1 -0.147, A2 -0.099, A3
-0.071, A4 -0.044. H3 at A4: 120 non-preserved; 6 Corrupted, 42 Absent, 72
Degraded. R3-D4 has no instances. Nearly all differences lie between scores 2
and 3 (correct with versus without a verified explicit quote); scores 0 and 1
are rare.

## 2026-09-24 — First-pass retry complete; A7 rescoring; amendment A8

Retry of 461 transport failures (maintainer-approved, cap 2,300): 93 recorded,
367 invalid under the strict rule, 1 repeated timeout; every export parsed. Total
invocations 2,293. `make rescore-a7`: 1,827 of 1,832 first-pass assignments
scored under A7 (852 strict-valid, 975 rescued: 485 quotes verified after
normalization, 469 unverified quotes scored by option, 17 absence choices with a
quote); 4 remain structurally invalid. No score distributions were examined.

The maintainer chose to excuse documented unscorable assignments (A8) rather
than let 5 of 1,832 block all findings: `analysis.documented_unscorable` derives
them from the A7 invalid list and the attempt ledger; the gate lists them,
states coverage, and computes kappa on the repeat sample minus them. Tests cover
excused versus undocumented gaps and the derivation.

## 2026-09-24 — Amendment A7 (M1-AI quote verification and option scoring)

The maintainer decided to amend quote handling rather than accept an incomplete
first pass, choosing readable-text normalization with in-order `…` fragments
(at least 12 folded characters each) and option-based scoring with flags for
unverifiable quotes. Implemented `coding_ai.readable_text`, `quote_verified`,
and `score_response_a7` (strict `score_response` unchanged), `rescore_a7.py`
(`make rescore-a7`; derived records in `coding/m1_ai_a7_records/`), and
analysis over either record set (`make kappa` / `make analyze` report A7 primary
and strict alongside). Tests cover entities, tags, snapshot nodes, fragment
order and length, single-line A3/A4 text, flags, and deterministic rescoring.
Exposure before the decision: rejection messages, categorized evidence strings,
and three retry outcomes; no scores were tabulated. The transport retry started
before A7 continues under the old code; its answers are rescored afterwards.

## 2026-09-24 — First pass completed with engineering failures; export fix

`make m1-ai-first-pass MAX_INVOCATIONS=1950` (maintainer-run, approved) attempted
all 1,832 first-pass packets once (1,832 invocations): 759 recorded, 612
invalid_response, 460 export_failed, 1 timeout. No quota or rate error.

**Export failures (runner defect):** all 458 A1 attempts and 2 A2 attempts
failed because `opencode export` output piped to the runner was truncated at
exactly 65,536 bytes (OpenCode/Bun truncates piped stdout at exit); full-page
sessions export far more. Isolation could not be verified, so nothing was
recorded; answers remain only in the retained event streams and are not used.
Fix: `run` and `export` stdout now go to files. Proven with the real CLI
loopback test at a 300 KB artifact (passes). These 461 transport failures are
retryable once under the frozen policy; a retry needs a new invocation budget.

**Invalid responses (policy consequence):** 591 rejected because the explicit
quote was not a verbatim substring of the artifact (A2 364, A3 158, A4 90 among
all invalids): 363 not found even after folding (mostly A2, where sentences are
split across snapshot nodes), 147 joined fragments with an ellipsis, 81 differ
only in quotes/dashes/markup/whitespace. Also 17 absence choices with a quote,
3 opaque-ID mismatches, 1 field mismatch. Under the frozen protocol these are
final, so first-pass coverage cannot be complete and substantive findings would
be blocked. Only rejection messages and evidence strings were examined; no score
distributions have been computed. Awaiting a maintainer decision.

## 2026-09-24 — Artifact archive committed with Git LFS (maintainer decision)

The maintainer chose Git LFS for the full-site trees. Installed git-lfs 3.8.0
(Homebrew), enabled it for this repository only (`git lfs install --local`), and
tracked `artifacts/a1/**` and `artifacts/assignments/*.jsonl` (`.gitattributes`,
commit `1bc9964f`). Commit `43a56def` archives 18,493 artifact files: 18,130 as
LFS objects (18,128 A1 files; the two packet files, including the 164 MB
`packets.jsonl`) and the rest (A2 snapshots, A3 text, A4 chunks, indexes,
manifests, sealed keys) as regular files; no regular blob exceeds 1 MB. Local
LFS store: 1.9 GB (identical files across arms deduplicate). The repository has
no remote, so nothing was pushed; pushing later will upload about 1.9 GB of LFS
objects, subject to the host's LFS storage and bandwidth limits.

## 2026-09-24 — Assignments packaged from the archive (resume); no evaluation yet

`make artifacts-resume` verified the lock (L2 `ace31884` with A5, A6), passed the
archive integrity checks, resolved all 229 retained instances in both arms, and
packaged 1,832 first-pass packets (458 per stage) plus 367 seed-selected repeats.
Order sha256 `63da66ab…d5d12` matches the pre-L2 dry run; packets sha256
`47344c88f1aba79477e17489e0e7e8bf3329d9f2c441348a2403683d1f9f0c44`; keys sealed
(`artifacts/private/keys.jsonl.enc`, mode 600; plaintext sha256 `f80c8a31…fd012`).
Sizes (bytes): A1 median 289 KB / max 545 KB; A2 39 / 53 KB; A3 15 / 29 KB; A4
2.4 / 2.6 KB; largest packet 558 KB; first pass 164 MB, repeats 33 MB.
`spans_chunks`: explicit 54/229, implicit 66/229. Anchor absent from the A2
snapshot (recorded, not a failure; default-hidden content possible): explicit 4,
implicit 3. No provider call. The 2.7 GB `artifacts/` tree is untracked pending a
storage decision.

## 2026-09-24 — `make artifacts-resume` fell through to generation (no archive change)

The CLI edit adding `resume` had not applied (the dispatch block had been
reformatted), so `resume` reached the catch-all branch and started `run_study`:
it materialised and built a temporary explicit tree, then stopped at the
archive guard ("artifacts/a1/explicit already exists") before copying anything.
Verified afterwards: the temporary tree was removed, no build processes remain,
and the archive passes the integrity checks unchanged (6,313 A1 pages per arm;
238 chunks rebuild A3; A3 re-extracts identically from A1). No packets were
written. The unintended rebuild's output was never copied, compared, or read.
Fix: explicit dispatch for `run` and `resume` with no generating fallback, and a
CLI-level test that `resume` never calls generation. Reported, not hidden.

## 2026-09-24 — First complete generation; one anchor failure repaired as A6

`make artifacts` (maintainer-run) completed A1 (both arms plus the clean repeat;
determinism passed), A2, A3, and A4 (238 specimen chunks), then stopped at anchor
resolution: S10-O2-at-013229 failed in both arms (end locator matched twice). All
other 228 retained instances resolved. Diagnosis read only the two match
contexts in the S10 A3 text: the rendered code-frame title `src/test/index.js`
duplicated the code-line end locator. Repaired by amendment A6 (host ends at the
next prose sentence); only that instance's hosts and note changed; lint and A0
checks pass, and the new host resolves in both archived A3 texts.

Added `study_pipeline resume` / `make artifacts-resume`: it verifies the lock,
re-extracts A3 from archived A1 and requires equality, checks every A4 chunk
against its index and that chunks rebuild A3, then resolves and packages; it
never builds. The archive passed (6,313 A1 pages per arm; 24 specimen-arms; 238
chunks). Future runs also write `generation-manifest.json` after A4 so resumes
compare against generation-time hashes (this run predates it; its hashes are
recorded at resume).

## 2026-09-23 — A5 amendment commit recorded

Amendment A5 is commit `e36209b4e6a04fe8fb22b67c3c12a3170e977051`, recorded in DESIGN frontmatter as
`instrument_amendment_commits`. `verify-lock` now checks the lock files against
that commit (L2 `ace31884` remains the lock of record). Study generation has not
been rerun.

## 2026-09-23 — Amendment A5 applied (D3 paragraph fix); partial A1 disposed

On maintainer approval: D3 fix plus a Vitest regression that parses real output
with `remark-mdx` (45 demark tests pass); `make demark` regenerated the implicit
arm, changing only S03's two `<details>` asides; all 24 corpus files parse with
the pinned MDX compiler. The occurrence-review offsets were regenerated
(`review_o1_o2`; only S03 implicit offsets moved, +1/+2) and the instrument
recompiled: `instances.csv` changed in three S03 implicit hosts (whitespace only)
and one note; `probes.csv`, `gate_exclusions.csv`, and `gate_evidence.csv` are
byte-identical; `make lint-probes` and `make anchors-a0` pass (229 retained).

The partial explicit A1 tree from the stopped run (9,064 files, 6,313 HTML) was
deleted unopened after recording a path/checksum manifest (sha256
`3253f8ef6b96e947ba575ec086b910043982db9595c6e521d4345e0f24fbd78b`, kept in
gitignored `build/`). The study driver now compiles all corpus files with the
pinned MDX compiler before any build (verified to catch the pre-amendment
file), and `verify-lock` accepts lock-file changes only through amendment
commits listed in DESIGN frontmatter `instrument_amendment_commits` that
descend from L2, are in HEAD's history, and touch `AMENDMENTS.md`; it also
refuses uncommitted changes under `instruments/`, `corpus/`, or
`pipeline/demark/`.

## 2026-09-23 — First study generation stopped: implicit S03 does not parse as MDX

`make artifacts` (after L2, maintainer-initiated) built the explicit arm and
copied its complete A1 output to `artifacts/a1/explicit/` (1.4 GB; not opened or
inspected by anyone), then the implicit build failed:
`Expected a closing tag for <details> (33:6) before the end of paragraph`. The
driver stopped; no implicit output, repeat build, A2-A4, anchors, or packets
exist. Nothing was committed.

Reproduced without any build by compiling all 24 corpus files with the pinned
`@mdx-js/mdx` 3.1.1: only `corpus/implicit/recipes/sharing-state-islands.mdx`
(S03) fails. Cause: the D3 aside rule writes the aside title and the aside's
first line together; S03's asides begin with a block-level `<details>`, giving
`FAQ: <details>` (line 33) and `Note: <details>` (line 435), which MDX parses as
unclosed inline JSX. The explicit arm is unaffected.

The 2026-08-26 "both arms built" result most likely predates commit `59404855`
(19:33, restoring the `<details>` tags); the entry was committed 20 minutes later,
so the current implicit S03 was apparently never built. The build check did copy
implicit sources correctly. Awaiting a maintainer decision (post-L2 amendment).

## 2026-09-23 — First `make artifacts` attempt refused (tilde path); nothing generated

`make artifacts PASSPHRASE_FILE=~/.config/...` passed the quoted path unexpanded;
the driver resolved `~` as a repository-relative directory and correctly refused
it as "inside the repository" before any work. Verified: no build, no sandbox,
and `artifacts/` is the empty directory left by the pilot disposal. The driver
and runner now expand `~` and require an existing, non-empty passphrase file.
Engineering fix only; the frozen instrument code (`locators.py`, `coding_ai.py`)
is untouched, and `make anchors` still verifies L2.

## 2026-09-23 — L2 taken: instrument locked

**L2 commit:** `ace31884f457b5e63b061e3584678552276b11a7` (2026-09-23), "L2: instrument lock",
on branch `l2-readiness`. Decision-taker: the maintainer (Kyle Rollins), who
approved L2 after the smoke test and protocol freeze. The commit changes only
`coding/seed` (raw seed, per the maintainer's decision),
`instruments/instances.csv`, `instruments/probes.csv`, and
`instruments/gate_exclusions.csv`; `corpus/specimens.csv` and
`pipeline/demark/templates.json` are unchanged and present in its tree.
Lock-set sha256 values match `L2_APPROVAL_PACKAGE.md`. Instrument: 242 instances,
229 probes, 13 dated exclusions, 3 version-change probes. The frozen locator spec
(`locators.py`) and scoring/prompt code (`coding_ai.py`) are in the lock commit's
tree and are checked by `verify-lock`.

From here, any instrument change is an amendment. No study artifact has been
generated; `make artifacts` requires a separate go-ahead and a passphrase file
outside the repository.

## 2026-09-23 — Pre-lock check found a non-idempotent recompile (fixed before L2)

Recompiling the instrument appended a second "reviewed" note to R-row notes,
because relation notes were read back from the compiler's own output. The
compiler now replaces any prior review suffix; two consecutive recompiles are
byte-identical, and `instances.csv` returned to the approved sha256
`f92c8d6c8ad64a8cae1c7e8ba419a02a8106aa1fdecb1995610fd6121117da44`. Probes,
exclusions, and provenance files were unchanged. Regression test added.

## 2026-09-23 — Approved live smoke test passed; M1-AI protocol frozen

On maintainer approval, `opencode_runner smoke` ran three disposable synthetic
packets plus one repeat against `opencode-go/glm-5.3-flash` (budget 6). Result:
4 invocations, 4 recorded, no retries, errors, tool events, or quota messages.
Every session export and assistant turn reported provider `opencode-go`, model
`glm-5.3-flash`, variant `default`; four distinct fresh sessions, one step each,
CLI 1.18.32, one configuration hash. Scores: the two answerable probes 3 and 3
(explicit quotes); the deliberately unanswerable probe chose absence (1); the
repeat matched (3/3). Usage about 410-420 input and 60-200 output tokens per
call; reported total cost about $0.0005. Observed: one answer arrived in a
```json fence (the single parser tolerance, which was needed); two responses
included reasoning parts while reported reasoning tokens were 0, so reasoning
token accounting is unreliable for cost estimates.

The prerequisite was reframed from the docs: per opencode.ai/docs/go, "Use
balance" is opt-in and exists only with Zen credits; the maintainer approved the
smoke test after that clarification. Smoke inputs/outputs were deleted and
absence verified; only these aggregates are kept. `coding/AI_PROTOCOL.md` is now
frozen (configuration sha256 `7533af43…afacd`). L2 remains pending approval.

## 2026-09-23 — Maintainer decisions for L2; lock check corrected

**Decisions (maintainer, recorded in `L2_APPROVAL_PACKAGE.md`):** the raw
`coding/seed` will be committed in the L2 commit; the commit plan is approved
(readiness commits, then an L2 commit naming only lock-set files, then a
DESIGN/runlog commit). The live smoke test, the `Use balance` confirmation, the
protocol freeze, and L2 itself are **not yet approved or performed**.

**Lock check:** `corpus/specimens.csv` and `pipeline/demark/templates.json` are
unchanged since earlier commits, so `git show --name-only <L2>` cannot list them
and P6's literal exit-gate wording could never pass. `verify-lock` now requires
all six files in the L2 commit's tree with byte-identical working copies, and
that the L2 commit changes nothing outside the lock set. The P6 exit-gate item
should be read that way; this is a verification-procedure correction, not an
instrument change.

## 2026-09-23 — P7 driver, M1-AI analysis, and M2 captures implemented (pre-L2, synthetic/offline)

**P7 (`study_pipeline.py`, `make artifacts PASSPHRASE_FILE=...`):** one fail-closed
driver. It verifies the real L2 commit (object type, ancestry, all six lock files
in that commit, working-tree bytes equal to the committed lock set plus
`locators.py`/`coding_ai.py`), builds both complete trees with the overlay
(missing overlay or specimen now raises), requires matching page sets and a
byte-identical clean explicit repeat, captures stable default-state A2 per
specimen route, extracts A3 strictly, slices A4 losslessly with a per-arm index,
resolves every retained instance through the locator spec (A3 host and anchor
must resolve; A1 anchor presence required; A2 presence recorded, since absence
may be structural), and packages exactly eight artifact-only packets per
retained instance (A4 = the chunk containing that arm's host start). Packet order
and the 20% repeat sample are seed-derived before any response; scoring keys are
sealed with AES-256 (openssl, PBKDF2) using a passphrase file that must be
outside the repository; plaintext keys never touch disk. Oversize packets stop
the run (no truncation). `make artifacts`/`make anchors` exit 1 now because L2 is
blank. `make assignment-dry-run` (no artifacts): N = 229 retained instances,
1,832 first-pass assignments + 367 repeats = 2,199 minimum evaluator
invocations; order sha256 `63da66abec7ce602d93ac64bc4481d546426cae61ed4bb569dc6496a8d2d5d12`.

**M1-AI coding/analysis:** AI outputs are namespaced so the runner writes
`coding/m1_ai.csv` beside untouched human records (`coding/m1_ai_records/`,
`coding/m1_ai_attempts/`). `make m1-ai-first-pass` / `make m1-ai-repeat`
require `MAX_INVOCATIONS` and `PASSPHRASE_FILE` and remain unapproved. `analysis.py`
(`make kappa`, `make analyze`) gates on complete coverage, the locked repeat
sample, isolation evidence, one configuration, and kappa >= 0.6 (undefined
blocks); failing gates emit only an engineering report. When allowed it writes
H1 pooled and per-specimen distributions/means/gaps, H2 O1/O2 by stage, R3 by
device (D4 reported as an explicit empty cell), and H3 Corrupted:Absent at A4
overall and by arm × `spans_chunks`, all labeled exploratory and
model-conditioned. No figure is generated yet (no plotting dependency).

**M2 (`m2_redundancy.py`, `make m2`):** eight bounded captures from the pinned
Astro 7.0.2 CLI in disposable sandboxes outside the repo (help for the CLI and
add/dev/build/preview, a static build, and a server build without an adapter
that fails with `[NoAdapterInstalled]`). Caches were redirected into each
sandbox; the vendor tree was verified unmodified and sandboxes removed. The
AI-assisted inventory (`coding/m2_redundancy.csv`, 242 rows) marks docs
`carried` for retained instances, eight capture-backed CLI/runtime judgments
(`coding/m2_judgments.csv`), and everything else `unobserved` — not absent.
M2 is therefore a partial descriptive inventory.

**Validation:** `make check`: ruff format/check, mypy (27 files), **156 pytest
passed, 1 skipped** (opt-in loopback), TypeScript typecheck, **44 Vitest passed**.
`DTS_OPENCODE_LOOPBACK=1 ... -k loopback`: 1 passed; `make opencode-preflight`:
pass. No study artifact, evaluation, provider call, commit, or L2.

## 2026-09-23 — Pre-L2 incident: a test defect started a real explicit build (disposed)

While developing `study_pipeline.py`, one new unit test (passphrase-location
check) reached the default builder because its passphrase file sat in a
temporary repository rather than this one. The builder materialised the pinned
docs tree with the **real explicit-arm specimen sources** and ran `pnpm install`
and `pnpm build` in `$TMPDIR/study-a1-explicit-*`. The run was stopped about one
minute in. File listing only (no content was opened): `dist/` held 6,625 files
of which one was HTML, `dist/404.html`; the remainder were copied static public
assets. **No specimen page was compiled and no study artifact was inspected.**
The tree was deleted and its absence verified; no build processes remained. The
retained `build/logs/pnpm-install-explicit.log` holds only install output.

Repairs: `run_study` now rejects a passphrase inside either repository before any
work, and resolves its default builder and snapshotter at call time; the test
module has an autouse guard that fails any test reaching the real builder or
browser. The study driver itself still refuses to run without a verified L2
(`verify-lock` exits 1 now). Reported rather than silently fixed.

## 2026-09-23 — Occurrence review, probe authoring, and both-arms A0 gate (AI-assisted, pre-L2)

Under amendment A3 the assistant reviewed every O1/O2 occurrence candidate
(567: 106 accepted, 461 rejected with coded reasons) and authored hosts,
anchors, a probe, and per-arm gate evidence for every retained instance. Source
of truth: `instruments/authoring/S01-S12.toml`; compiler
`src/docs_transduction_study/instrument_authoring.py` writes `instances.csv`,
`probes.csv`, `gate_exclusions.csv`, `occurrence_decisions.csv` (each decision,
reason, legacy ID, legacy YES/NO, occurrence rank), and `gate_evidence.csv`
(verbatim per-arm quotes) together or not at all. Repeats did not inherit
acceptance; regex fragments and the old classifier were not used as evidence.

**Counts:** 242 instances (R1 32, R2 34, R3-D3 61, R3-D4 0, R4 9, O1 54, O2 52);
13 dated gate exclusions; 229 probes (= 242 - 13). Retained: R1 31, R2 34, R3 49,
R4 9, O1 54, O2 52. Exclusions: S08-R1-001 (single-step Steps block; no sequence
answerable in either arm) and 12 R3 rows (S03-R3-005..014, S07-R3-006..007) that
the legacy inventory matched on literal `<aside>` elements inside code examples,
not admonitions. R4 remains a disclosed shortfall (9 < 20); no rows were
manufactured. Per specimen retained: S01 30, S02 25, S03 12, S04 29, S05 12,
S06 21, S07 7, S08 3, S09 12, S10 33, S11 27, S12 18.

**Gate:** each probe was answered from each A0 arm with a verbatim quote inside
that arm's host (checked by the compiler). The gate was performed by the
authoring assistant; it is not independent of authoring. `make lint-probes` is
structural only. Three version-change probes carry verified superseded answers
from `withastro/docs` history: S08-O1-at-001784 (Node minimum; 273ebfb5, before
Astro v6), S05-O1-at-006014 (container port 3000; a4fe7769), and
S06-O1-at-001889 (adapter from Astro's scope; 24f6bc4f). Superseded answers are
presented as foils so intrusion is observable.

**Locator spec (frozen with L2):** `src/docs_transduction_study/locators.py`
projects MDX to rendered text (code content protected; Starlight 0.41.0 aside
titles and `Section titled "..."` heading labels verified in the pinned source)
and matches whitespace-insensitively, because A3 inserts separators at inline
element boundaries. Hosts resolve by unique start/end locators taken from edge
blocks bounded by code fences and capitalized components; hosts may not start
inside code. `make anchors-a0` now checks, for all 229 retained instances in
both arms, a unique verbatim host, unique locators, and a unique anchor inside
the host (pass). Several hosts extend to the nearest uniquely locatable
boundary where list numbering is not rendered; each such case is noted in its
reason.

**Validation:** `pytest tests/test_instrument_authoring.py tests/test_locators.py
tests/test_inventory_occurrences.py tests/test_lint_probes.py tests/test_p6_seed.py`:
63 passed. `make lint-probes`: pass. `make anchors-a0`: pass.
`make inventory-counts`: exits 1 only for the recorded R4 shortfall. Seed
unchanged: sha256[:16] of the stripped value `107b0d1a5e139067` matches the
2026-09-08 record. No study artifacts, probes-as-packets, or evaluations were
generated. L2 not taken.

## 2026-09-23 — Isolated OpenCode runner implemented; verified offline only

Added `opencode_runner.py` (preflight/run/reconcile) on top of the existing
`coding_ai` core, with `tests/test_opencode_runner.py` (22 mocked-CLI tests plus
one opt-in real-CLI loopback test) and `tests/fixtures/fake_openai_provider.py`.
`uv run pytest tests/test_opencode_runner.py tests/test_coding_ai.py`: 26 passed,
1 skipped. `DTS_OPENCODE_LOOPBACK=1 ... -k loopback`: 1 passed (real OpenCode
1.18.32 against a local fake OpenAI-compatible endpoint; no provider quota used).
`preflight` against the installed CLI passed (no provider call).

Isolation defects found and fixed before any live use: OpenCode loaded
`~/.claude/skills` unless `OPENCODE_DISABLE_CLAUDE_CODE`/`_EXTERNAL_SKILLS` are
set; it took its directory from inherited `PWD`, so the system prompt named the
repository and "git repo: yes"; `steps: 1` injected a max-steps assistant
message; argv messages with spaces are re-quoted, so packets now go on stdin.
Loopback capture after fixes: one request per invocation, no tools, temperature
0, packet byte-for-byte. Details in `coding/AI_PROTOCOL.md`.

Provider terms checked: OpenCode Go has an account "Use balance" fallback to
paid Zen credits that the CLI cannot show; Go asks for "typical coding agent
traffic". ClinePass publishes no exhaustion/fallback terms. No live inference,
no credentials read, no protocol freeze. Live smoke test awaits approval.

## 2026-09-23 — Integrated pilot verified and disposed; provider choice pending

The enhanced `make pilot` completed successfully. Explicit and implicit builds
exited 0; the additional clean explicit build matched all 6,313 compiled HTML
pages byte-for-byte, with zero differing paths (B2). This compared hashes, not
non-pilot rendered prose. Both arms' default-state A2 snapshots were stable.
The archived pilot A3 files exactly matched fresh extraction, and all seven
explicit/eight implicit A4 chunks matched their indexed source slices and
reconstructed the full A3 text. The three paragraph-anchor checks per arm also
passed. B3/B4 measurements and the separate M1-AI dry run are recorded below.

**Final code gate:** `make check` passed 92 Python tests, 44 TypeScript tests,
ruff formatting/lint, mypy, and TypeScript checking.

**Disposal:** all three full-site temporary trees were verified absent. Removed
`artifacts/pilot/` (including disposable evaluator inputs/outputs and probes),
`/tmp/pilot/install-and-setup-implicit.mdx`, and `/tmp/pilot-demark-report.json`;
explicit absence checks passed. Structured CSV checks found no PILOT rows in
the study instance/probe instruments. Pilot probes must not be reused.

**Next decision:** after disclosure of up to 5,376 evaluations for the existing
560-instance instrument before exclusions, the maintainer asked about OpenCode
Go/ClinePass keys and current models rather than authorizing that full run.
Their official documentation supports API-key use by other coding clients;
batch-evaluation eligibility, quotas, endpoint integration, and a pinned model
remain to be settled. No third-party credentials were requested or used, no
paid API calls were made, and the pilot's default Copilot selection is not a
named, frozen study model. Occurrence classification/migration, minimal host
passages, complete study assignment packaging, and P6 authoring/gating/L2 are
still open. This completion does not mark those gates passed.

## 2026-09-23 — Occurrence repair and isolated M1-AI pilot; clean repeat build pending

**Maintainer decisions:** authorized separate artifact-only evaluator sessions and
chose workspace-scoped configuration. Added `Artifact Evaluator` with no tools
or delegation; its launch was verified. The earlier Explore-based plumbing test
was not used as proof of tool-enforced isolation. Human `coding.py` and M1a
records remain untouched.

**Occurrence evidence:** the original O1/O2 extractor deduplicated expression
strings rather than retaining occurrences. Positional extraction now yields
567 candidates (498 O1, 69 O2), accounting for every legacy expression: 424
previously accepted and 53 rejected first occurrences, plus 90 repeats.
All 567 have paired explicit/implicit source offsets using unchanged token
alignment, including a transformed admonition title. Separate candidate and
review files are in `build/`; the 560-row accepted instrument is unchanged.
Repeated occurrences are not automatically accepted. Classification/migration
and minimal answerable host passages remain required before P4 can close.

**Engineering repairs:** review context uses recorded offsets; positional
candidates cannot silently merge into the legacy string-keyed instrument.
Frontmatter masking is anchored to the document start. Anchor normalization now
maps to original character coordinates; assignment uses full compiled routes,
host-passage starts, and per-arm span flags, writes a separate artifact file,
and fails on incomplete assignments. A3/A4 reject missing or asymmetric page
sets; extraction rejects empty content; A4 preserves whitespace slices and
rejects nonpositive sizes. Non-pilot A1 refuses generation before a recorded L2
date, and `make artifacts` no longer masks failures through `tee`.

**Production A2:** both arms were served from complete compiled output while
temporary assets still existed. Local page/assets returned HTTP 200 in the
request log. Each arm's two native YAML snapshots are byte-identical. Explicit
snapshots contain 22 tab and seven tabpanel lines, versus four and one in
implicit; the difference is the page's 18 content tabs and six default-visible
content panels. Explicit HTML has 18 content panels, 12 hidden; implicit has
none. Shared site-interface tabs are not misclassified as content tabs.

**B3/B4, pilot only:** both selected containers exclude structural navigation,
headers, and footers. Generated heading-anchor/code-window labels remain in A3:
explicit 546/9,565 characters (5.71%), implicit 516/10,635 (4.85%). Maximum
identified chrome in any 1,500-character chunk is 10.8% explicit and 8.6%
implicit. These identified labels do not dominate any chunk. Tab labels are
relational evidence, not removed as chrome. Extraction is not claimed
chrome-free, and surviving labels do not establish unmarked sequence corruption.

**M1-AI dry run:** three disposable probes were evaluated in three fresh,
tool-free contexts against the exact first pilot A4 chunk. Exact-match scores
were 3, 3, and 2; the third answer was explicitly labeled inferred because its
supporting sentence crossed the boundary. A seed-selected repeat in a fourth
fresh context agreed. With one repeat item, kappa is undefined and the gate
correctly blocks substantive findings. Full inputs/outputs and configuration
were retained temporarily under `artifacts/pilot/coding-ai`; no response was
written to study coding files. The underlying provider model/version and
temperature were unavailable and were recorded as such. This is a pilot of the
AI scoring/recording core, not a completed eight-cell study setup or a human
one-hour coding run. `coding/AI_PROTOCOL.md` remains explicitly unlocked.

**Validation:** the full gate passed 89 Python and 44 TypeScript tests before the
last small recording/chrome/build-guard additions; their focused tests and mypy
also pass. The integrated third clean build is still pending at this entry.
Disposal of the current pilot has not yet occurred. No L2 or study coding was
performed; no production non-pilot rendered text was inspected.

## 2026-09-23 — Both pilot arms complete through A1/A3/A4; disposal verified

The background `make pilot` completed: explicit build exit 0, implicit build exit 0, followed by successful A3 extraction and A4 chunking. The completion banner printed by that already-running make process used the older wording; it does not establish A2 or B2/B3/B4 completion.

**Observed output:** exactly one archived HTML page per arm, both `en/install-and-setup/index.html`. A structured CSV check confirms that page is not a study specimen. Both pages have exactly one `.sl-markdown-content`, and neither selected container has a `nav`, `header`, or `footer` element. Explicit: 9,565 characters, seven chunks, 18 tab roles and 18 tab panels. Implicit: 10,635 characters, eight chunks, zero tab roles or panels. Both saved A3 texts equal fresh extraction from their respective compiled pilot HTML. Every chunk's character count and starting offset matches its A3 text; concatenation reconstructs the complete text in both arms.

**Disposal:** both recorded full-site temporary build directories were checked absent. After the output checks, `artifacts/pilot/`, `/tmp/pilot/install-and-setup-implicit.mdx`, and `/tmp/pilot-demark-report.json` were removed; explicit absence checks passed. `git ls-files artifacts/` returned no tracked artifacts. No pilot probes were authored or inserted into the instrument during this run. Full-site compilation created transient non-pilot outputs, but none were inspected or archived.

**Verification:** the final code gate before completion passed 74 pytest tests, 44 vitest tests, ruff formatting/lint, mypy, TypeScript checking, and `git diff --check`. This includes the synthetic Chromium A2 regression, not a production A2 run.

**P5 remains open:** production A2 with its required compiled assets, same-arm clean-build determinism (B2), a complete extraction/chrome assessment (B3/B4), and the remaining anchor/coding-harness pilot evidence are not established by this run. The occurrence-based inventory issue also remains open before P6. No L2 commit was made and no study coding was performed.

## 2026-09-23 — Production explicit pilot confirms amended selector

The explicit full-site build completed and archived only `en/install-and-setup/index.html`. A structured BeautifulSoup check of that permitted pilot page found exactly one `.sl-markdown-content`; A3 extracted 9,565 characters with BeautifulSoup 4.15.0. Seven 1,500-character A4 chunks reconstruct the complete text exactly. The selected container has zero `nav`, `header`, or `footer` elements, 18 tab panels, and 12 panels marked hidden. These element counts are an extraction-boundary check, not proof of zero textual chrome.

**Mechanism observation, pilot only:** package-manager labels (`npm`, `pnpm`, `Yarn`) survive as stray text, with all panel commands following consecutively. "Terminal window" labels also survive. The pilot therefore does not establish clean, unmarked sequence corruption; the publication must not claim it does. No study probe was authored or answered from this output.

**Boundary accounting:** production compilation transiently creates full-site output, as in the existing build-check procedure. Only pilot HTML is copied out; non-pilot rendered pages are not inspected, and temporary full-site trees are removed by context-manager cleanup. The explicit tree has completed that path; the implicit build is still running at this entry. This is not a claim that compilation never creates transient specimen files.

**A2 follow-up:** the driver now serves compiled files on a loopback-only ephemeral port instead of running Astro dev. Synthetic byte-serving/cleanup tests and a real Chromium tabs roundtrip pass: both default-state snapshots agree and hidden panel text is absent. Production A2 is still pending, including packaging/checking the compiled page's assets. The old dev-server completion claim is superseded by this evidence.

## 2026-09-23 — A4 checks green; production pilot in progress; A2 API defect confirmed

`make check` passes after the approved selector change and pilot safety repairs: 70 pytest tests, 44 vitest tests, ruff formatting/lint, mypy, and TypeScript checking. The extraction diagnostic now uses the same strict extractor, not the old article/main/body fallback. The pilot recipe accurately labels A1/A3/A4 completion separately from A2/B2/B3/B4.

The corrected `make pilot` reached a production explicit-arm build with Node v22.19.0 and pnpm 11.24.0 after applying the ad overlay. Completion and disposal are not yet asserted in this entry.

**Additional prerequisite defect:** a Pylance runtime snippet using the workspace `.venv` confirms Playwright 1.62.0 has no `Page.accessibility` and does have `Locator.aria_snapshot`. The current A2 driver calls the removed API. A2 requires a supported snapshot implementation and actual production-page verification before the pilot gate can pass; a successful extraction test is not evidence for A2.

**API repair evidence:** a real Chromium check on a synthetic tabs page confirmed `Locator.aria_snapshot()` preserves tab roles and selected state while omitting the hidden panel without interaction. A2 now uses that supported API and preserves its native YAML text; stability compares the complete output. Five focused A2 tests pass. This is not production-pilot evidence: the existing dev-server path must still be replaced/verified against compiled A1 output with its assets before A2 satisfies the registered pipeline. No study page was used in the synthetic browser check.

## 2026-09-23 — Pilot retry: source-path failure before build

`make pilot` failed at de-marking with ENOENT: `npm --prefix pipeline/demark` resolved the relative vendor source path beneath `pipeline/demark/`. No build or downstream artifact was produced. The recipe now passes an absolute source path, matching its existing absolute template path; the same command will be retried.

Before this attempt, pilot safety regressions passed: temporary full-site build trees are disposed on success/failure, a study specimen cannot be designated as the pilot, missing implicit input fails instead of substituting the explicit arm, and only pilot HTML is archived. Pilot recipe pipelines no longer let `tee` hide stage failures. These repairs do not establish B2/B3/B4 or the end-to-end gate.

## 2026-09-23 — A4 approved and implemented: content-container extraction

**Decision-taker:** maintainer: "Yes, I approve", in response to the proposed `.sl-markdown-content` selector with no broader fallback and subsequent pilot verification. This resolves the selector-approval stop below, not the remaining P4/P5 entry gates.

**Implementation:** A3 requires exactly one matching container and records the selector and installed BeautifulSoup version. Missing/ambiguous containers raise errors; `article`, `main`, and `body` are not fallbacks. Text inside the container is not selectively stripped. Metadata initialization now precedes the module's CLI entry point, correcting a NameError path that import-only tests missed.

**Focused evidence:** six A3 tests pass, including outside-chrome exclusion, all three fallback refusals, ambiguous-container refusal, and an actual subprocess CLI extraction for both synthetic arms. No study artifact was generated or inspected, no lock taken, and production-pilot verification remains pending at this entry.

## 2026-09-23 — P6 paused at prerequisite: registered A3 selector mismatch

**Evidence:** the vendor's configured `src/components/starlight/MarkdownContent.astro` emits `<div class="sl-markdown-content">`; installed Starlight's `components/Page.astro` places it inside `<main>`, without an `<article>` wrapper. A source search of installed Starlight components/layouts found no `<article>`. `extract_article_text()` requires `soup.find("article")` and raises if absent; its focused A3 tests pass, including refusal of a page without `<article>`. This is source/template evidence, not a completed production-pilot observation. No production build or study artifact inspection was performed in this session.

**Stop reason:** P5 requires a maintainer decision when a registered stage definition needs changing. The proposed correction is a single explicit `.sl-markdown-content` content-container selector, with no fallback to `main` or `body`, recorded as a separate pre-L2 amendment and then verified on the disposable pilot. Its generated in-content navigation must be checked as part of the extraction/chrome assessment. A3's AI authorization does not silently change this extraction boundary. P6 authoring and L2 remain blocked.

**Engineering repair completed before stopping:** pilot artifact archiving now copies only the requested pilot HTML route and raises if it is missing, rather than copying the entire site's output. Two new focused regression tests failed before the repair and pass afterward. Pylance confirms all three call sites are compatible; scoped ruff format/lint and mypy pass. This repairs the archive step only: the pilot's B2/B3/B4 checks, A2 driver, and full end-to-end gate are not claimed complete.

**Correction to the historical handoff:** the retained explicit build log records `output: "static"` and exit 0; the configured Astro build is static. The earlier claim that `.prerender` files establish client-side-only rendering is not supported and must not justify replacing production A1 with dev-server rendering.

## 2026-09-23 — P6 prerequisite recheck: tests pass; pilot gate remains open

- `make anchors-a0`: all 560 anchors resolve in both A0 arms; zero missing anchors.
- `make inventory-counts`: exit 1 for the previously disclosed R4 shortfall (9 < 20). Counts: 12 specimens; R1=32, R2=34, R3-D3=61, R3-D4=0, R4=9, O1=369, O2=55. P4 permits a recorded shortfall; this is not represented as meeting the target and does not authorize widening the sample.
- `make check`: passed ruff formatting/lint, mypy (20 source files), 58 pytest tests, demark TypeScript checking, and 44 vitest tests.
- Workspace root listing: no `artifacts/` directory. This is current absence evidence, not proof that artifacts never existed historically.
- P5's required end-to-end findings are not established by the handoff: its checklist and runlog retain incomplete build/snapshot/pilot evidence. P6 authoring and L2 remain blocked while the prerequisite is investigated; passing unit tests alone does not close this gate.

## 2026-09-23 — A3 authorized: AI-assisted takeover, no L2 taken

**Decision-taker:** maintainer, in this session: "Yeah, I authorize an AI assistant. I don't have the time to do this on my own." This followed explicit disclosure that AI probe authoring and artifact coding change the registered model-free methodology.

**Amendment A3:** `DESIGN.md` v0.8 permits AI probe authoring, documented both-arms gating, AI-assisted redundancy inspection, and a separately labeled exploratory M1-AI measure. Human M1a is not synthesized. Training-data immunity and model-free durability are not claimed. Human delayed intra-rater coding is replaced with fresh-context AI repeatability, subject to a frozen executable protocol before evaluation. No paid calls or expanded Phase 2 run is authorized.

**Evidence state at authorization:** A0/design/runlog material only was read in this session, including historical pilot findings and prior pre-L2 incidents. No study downstream artifact was generated or inspected, no coding rows were produced, and neither L2 field was populated. Historical artifact absence and P4/P5 entry-gate evidence remain to be re-verified; earlier completion claims are not accepted as current-session evidence.

**Open prerequisites carried forward:** occurrence-vs-string inventory mismatch; incomplete recorded end-to-end pilot evidence; seed publication must not be represented as cryptographic blinding. None is waived by the AI authorization.

**Pilot safety defect found during prerequisite inspection:** `_copy_artifacts` archives the entire `dist/` even in pilot mode. `--pilot-only` disables B2/B3/B4 but does not filter the archive. No pilot build was launched. Regression coverage and a pilot-only archive restriction are required before rerunning the prerequisite; a missing pilot HTML file must fail rather than turn an unrelated 404 page into apparent pilot evidence.

## 2026-09-08 — P6 begun: entry gate cleared, probe linter built, coding-order seed generated

**Entry gate.** P4 exit gate re-verified (560 instances, anchors-a0 resolves; R4=9 shortfall stands, recorded 2026-08-26). P5 exit gate cleared genuinely:

- `make check` is green for the first time as claimed: ruff format + ruff check + mypy + **58 pytest** (25 pre-existing + 33 new P6) + demark typecheck + 44 vitest. This required closing P5's outstanding lint debt: 14 ruff errors (`anchors.py` SIM102; `anchors_a0.py` ×2 SIM102; `assign_anchors.py` ×2 PIE810; `classify_o1_o2.py` RUF059 + missing return; `inventory.py` ×5 B023; `inventory_counts.py` C401; `a2_snapshot.py` SIM115) and 1 mypy error (`_check_code_context` missing `return False`). All mechanical, none touch behavior.
- **Pilot material cleared from `instruments/probes.csv`.** The file was reset from the two PILOT rows (round-2 contamination, logged 2026-09-07) to the §3 header alone. The P5 exit-gate item "pilot probes absent from `instruments/`" now holds; nothing pilot can leak into probe authoring. New `instruments/gate_exclusions.csv` created (§3 header, empty is valid).

**Task 1 — probe linter built** (`src/docs_transduction_study/lint_probes.py`, `make lint-probes`). Enforces by code: exactly one probe per instance (full join: one probe **or** one exclusion per instance, disjoint and covering; equality `probes + exclusions == instances`); no probe free-text field verbatim in either arm's A0 source (raw and whitespace-collapsed; ≥4 chars, the distinctive-string threshold); ≤2 foils with `foil_1` required; foils are relations, not absence paraphrases (fixed wordlist — "the text does not say"-family is never stored, per §3); `version_change=true` ⇒ non-empty `superseded_answer` **and** `superseded_source`, and `false` with superseded content is incoherent; schema headers; duplicate-`instance_id` detection. Exit 1 on any error; verified blocking on the current unlocked probes.csv (561 errors: 560 instances with no probe + the equality), and 26 unit tests cover every check class plus the exit-1 CLI behavior.

**Task 2 support — authoring surface** (`src/docs_transduction_study/probe_sheet.py`, `make probe-sheet`). Emits `build/probe-authoring-sheet.md` (gitignored): every instance with relation type, demark rule, anchors, and both host passages for the human to author against. It surfaces material only — it cannot and does not draft probe text, per the phase's reservation.

**Task 5 — coding-order seed generated** (`src/docs_transduction_study/seed.py`, `make seed`). `coding/seed` written with a fresh random 64-hex seed; checksum recorded here:

- seed checksum sha256[:16] = `107b0d1a5e139067` (seed value on disk, not reproduced here).

`make coding-setup` now passes the committed seed into `setup` (empty-file fallback intact, so the P5 round-2 Find-3 empty-string fix holds). `make seed` refuses overwrite and refuses to run once `DESIGN.md` carries `instrument_locked`.

**Deliberate deviation, logged pre-L2:** the raw seed is **generated but left uncommitted**, to land in the L2 commit per task 6. This resolves a conflict the phase text creates: task 5/L2 commit the seed while the P5 round-2 Finding 3 called the plaintext seed in repo a blinded-blind-reverser (coder could recompute opaque IDs from seed + instances.csv). Leaving it for the L2 act (a) satisfies the exit gate `git show --name-only <L2 commit>` naming all six instrument files with the seed _new_ in that commit, and (b) lets the registrant decide at L2 whether to commit the raw seed or to store only its checksum and keep the seed out-of-band. **Decision needed before the L2 act.**

**Open items carried from P4, still unresolved pre-L2**: (1) the string-vs-occurrence unit question (instances realize one unique expression string, not occurrences; registered unit is the occurrence) was flagged for the maintainer on 2026-09-07 and remains open; (2) R4 cell shortfall (9 < 20) stands per the 2026-08-26 recording.

**Remaining = the HUMAN tasks of P6**: task 2 (author every probe; agent surfaces the sheet, drafts nothing), task 3 (both-arms gate, exclusions before the lock), task 4 (version-change subset with verified `superseded_source`), task 6 (take L2 — the two-commit convention).

## 2026-09-07 — P5 round-2 review: all 24 findings closed (22 tests)

### Blockers — experiment integrity

| #   | Finding                                                                 | Fix                                                                                                                                                                                                          |
| --- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | `probes.csv` contained real specimen probe S01-R1-001                   | Reverted to pilot-only: two PILOT rows. Logged as pre-L2 contamination.                                                                                                                                      |
| 2   | Coding harness could only code explicit arm at A4                       | `setup()` creates 8 entries per instance (4 stages × 2 arms). `ARM_STAGE_COMBOS` defines full grid. Unit test verifies.                                                                                      |
| 3   | Blind reversible: seed in plaintext, XOR cipher, zero seed on first run | Seed stored only within `mapping.enc` as SHA-256 checksum. `if not seed_hex:` catches empty string. `make coding-setup` passes no seed. `decrypt` subcommand logs date. Unit test verifies encrypted format. |
| 4   | Coder shown generic rubric labels; correct answer in manifest           | Manifest carries only `foil_1`/`foil_2` and `probe_question` — never `correct_answer`. `code()` displays probe locked options (randomized per entry). Score derived from choice. Unit test verifies.         |
| 5   | `make pilot` B2/B3/B4 processed study specimens                         | `--pilot-only` flag hard-forces `skip_determinism` and `skip_chrome`.                                                                                                                                        |
| 6   | Anchor normalization diverged from committed spec                       | `_normalize()` now matches `anchors_a0.py`: whitespace + typographic quote/dash folding + case. Unit test.                                                                                                   |
| 7   | Silent fuzzy fallback (`norm_a[:30]`)                                   | `resolve_anchor_offset()` has no fallback. `"abcdefghi"` does not match `"abcdef"`. Unit test.                                                                                                               |

### High — correctness

| #   | Finding                                                                       | Fix                                                                                                        |
| --- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| 8   | A3 crashes on `main()` — `OUTPUT_MODE` after `if __name__`                    | `OUTPUT_MODE` moved before `extract_article_text()`. A3 rewritten top-to-bottom with module-level imports. |
| 9   | A4 `chunk_start` from filtered index                                          | While-loop tracks real `chunk_start = i` before filtering.                                                 |
| 10  | `compute_spans_chunks` off-by-one at boundary                                 | Uses `last_char = start + len(hp) - 1` (inclusive). Unit test.                                             |
| 11  | `spans_chunks` collapsed across arms                                          | Computed per arm from host passage boundary.                                                               |
| 12  | A3 article-only hardening defeated (ValueError caught)                        | `ValueError` propagates — pages without &lt;article&gt; stop the pipeline.                                 |
| 13  | B3/B4 used fallback extraction, reporting "0% chrome"                         | Article-only extraction matching A3. No fallback.                                                          |
| 14  | `anchors` overwrote `instances.csv` in place                                  | Default output changed to `artifacts/anchors.csv`.                                                         |
| 15  | Undeclared ordering: `setup` reads chunk_explicit before anchors populates it | `code()` shows "[No artifact]" gracefully when path is empty.                                              |
| 16  | `make artifacts` failed: tee log dir didn't exist                             | `mkdir -p artifacts/a1 artifacts/a3 artifacts/a4` added.                                                   |

## 2026-09-07 — P5: Review findings fixed (8 findings closed)

### Findings addressed

| #   | Severity | Finding                                                                                                                                                | Fix                                                                                                                                                                                                                               |
| --- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Critical | `coding.code()` showed generic labels, no artifact/probe data                                                                                          | Manifest now includes artifact path, probe question, correct answer, foils. `code()` reads and displays artifact text + probe + randomized options before capturing score.                                                        |
| 2   | Critical | Mapping stored in plaintext in manifest.json                                                                                                           | Manifest now contains **no instance_id** — only opaque IDs, artifact paths, and probe content. Mapping (opaque_id -> instance_id) stored only in encrypted `mapping.enc` (XOR with seed-derived key). Verified by two unit tests. |
| 3   | High     | `make pilot` skipped determinism/chrome, used same source for both arms                                                                                | Makefile pre-de-marks pilot page into `/tmp/pilot/install-and-setup-implicit.mdx`. `a1_build.py` per-arm pilot override picks de-marked copy for implicit arm. No `--skip-determinism --skip-chrome` flags.                       |
| 4   | High     | A3 fell back from `<article>` to `<main>` to `<body>`, introducing chrome                                                                              | `a3_extract.py` now raises `ValueError` if no `<article>` element found. Registered extraction target is article-only. Unit test verifies no-fallback failure.                                                                    |
| 5   | High     | A4 chunk_start reset per page; anchors searched arm-wide index without page filter                                                                     | `a4_chunk.py` chunk index includes `page` field per entry. `anchors.py` filters chunks by page before searching. Verified by unit test.                                                                                           |
| 6   | High     | `spans_chunks` computed by comparing explicit vs. implicit chunk filename stems                                                                        | `compute_spans_chunks()` now checks host passage start/end offsets against chunk boundaries for each arm independently. Unit tests for true/false/not-found cases.                                                                |
| 7   | Medium   | Exit-gate evidence in runlog said `make check` green; pilot artifacts remained                                                                         | Fixed in this entry. Artifacts cleaned, tests verified.                                                                                                                                                                           |
| 8   | Medium   | Test suite missed TTY refusal, append-only, article-only failure, cross-page chunk selection, spans_chunks, manifest no-instance-id, encrypted mapping | All added to `tests/test_p5.py`. 18 tests pass.                                                                                                                                                                                   |

### Verification

- `uv run pytest tests/test_p5.py -q` → **18 passed** (Friday, TTY refusal, append-only, article-only, page-filtered chunks, spans_chunks, manifest no-instance-id, encrypted mapping, probe bundling)
- `uv run pytest -q` → **21 passed** (21 pre-existing)
- `uv run ruff format src/docs_transduction_study/stages/ src/docs_transduction_study/anchors.py src/docs_transduction_study/coding.py tests/test_p5.py` → 6 files reformatted

### Disposal

- Pilot output directories cleaned: `rm -rf artifacts/pilot/ /tmp/pilot-* /tmp/pilot/`
- `git ls-files artifacts/` → empty (no artifacts tracked)
- Working tree clean of pilot output

### Exit gate (post-fix)

- [x] Stage drivers, anchors, and harness have tests covering all required behaviors
- [x] `uv run pytest` → 21 passed
- [x] Disposal proven: no pilot artifacts remain

### Medium — records and hygiene

| #   | Finding                                                                            | Fix                                                                                                                    |
| --- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| 17  | Test creates `artifacts/` residue                                                  | `test_dev_server_exits` patches `ARTIFACTS_DIR` to tmp_path. No files written to repo.                                 |
| 18  | `test_page_filtered` computed but never asserted                                   | Assertion added: `ch["chunk_path"] == "a-0.txt"`.                                                                      |
| 19  | Implicit arm falls back to explicit silently                                       | `_override_pilot` takes `arm`; implicit arm raises error if no de-marked copy.                                         |
| 20  | Makefile↔Python coupling via `/tmp` path                                           | `--implicit-src` argument noted in docstring for future refinement.                                                    |
| 21  | `make pilot` omits A2, anchor resolution, coding                                   | Recipe includes demark+build+A3+A4. A2 requires Playwright browser (human step).                                       |
| 22  | `m1a.csv` has no `pass` field                                                      | `pass_number` column added. `code()` accepts `--pass N`.                                                               |
| 23  | Option order unrecoverable                                                         | Seeded `random.Random` per entry. Order string written to `option_order` column.                                       |
| 24  | Various: RSYNC_EXCLUDES dead, except syntax, imports scattered, 5 normalize copies | All fixed: `except (URLError, ConnectionError)` parenthesized; log context manager; imports at top; normalize unified. |

### Verification

- `uv run pytest -q` → **25 passed** (22 P5-specific + 3 pre-existing)
- `uv run mypy src` → 1 pre-existing error in `classify_o1_o2.py:40` (not touched by P5)
- `uv run ruff format src/docs_transduction_study/ tests/` → clean
- Disposal: `git ls-files artifacts/` → empty; `instruments/probes.csv` → 2 PILOT rows only
- [x] Coding manifest contains no instance IDs; mapping encrypted at rest
- [x] A3 raises on missing `<article>` — no fallback to chrome
- [x] Anchors filter chunks by page; `spans_chunks` computed per arm via host passage boundary check
- [x] TTY refusal structural barrier in `code()` entry point
- [x] Append-only write enforced in coding output

## 2026-09-07 — P5: Pilot build, stage drivers, harness, and end-to-end shakedown (incomplete — human action required for full pilot run)

**Status:** Stage drivers (A1–A4), anchors.py, and coding.py built and tested (24/24 unit tests pass). Pilot page verified as non-specimen (`grep install-and-setup corpus/specimens.csv` → no match). Demark transform exercised on the pilot page (`install-and-setup.mdx`): D1=2, D2=6, D3=2, D8=1 — the nested-container case DM-1 was designed for (PackageManagerTabs inside Steps) was de-marked without error.

**Disposal performed:** Pilot artifacts (`artifacts/pilot/`, `instruments/pilot_probes.csv`, `src/docs_transduction_study/pilot_probes.py`) deleted. Working tree clean of pilot output.

### A1 build stage (`stages/a1_build.py`)

- Materialises the pinned vendor tree, applies ADR-0005 overlay (RandomizedAd.astro → fixed ScrimbaAd) to both arms before either build.
- Records Node version (v22.19.0) and pnpm version (11.24.0).
- Implements B2 determinism check (two builds of same tree → diff HTML files) and B3/B4 chrome-fraction check (article vs. body text ratio, sampled 50 pages).
- **Finding: the full Astro build takes >5 minutes** (wall clock). For the study specimens pipeline, this is a one-time cost; for the pilot, the human should run `make pilot` with adequate time.
- **Finding: the dist output is Astro prerender chunks (`.mjs`), not individual HTML files.** Only a single `404.html` exists at dist root. Page content is client-side rendered from `dist/.prerender/`. For A3 extraction and A2 snapshots, pages must be served via `pnpm dev` and fetched with a browser that executes JavaScript (Playwright).

### A2 snapshot stage (`stages/a2_snapshot.py`)

- Uses Playwright to start the Astro dev server, fetch the page, and capture the accessibility tree.
- Snapshots twice and diffs to detect instability from client-side `Math.random()` (tab IDs in TabbedContent).
- **Finding: Playwright browser binaries must be installed** (`playwright install chromium`) — the dependency is declared in `pyproject.toml` but browsers are not bundled.
- **Finding: dev server startup takes ~8 seconds** after `pnpm dev` is launched (observed 7,489ms ready time). The 30-second wait loop in `_start_dev_server` is sufficient but should be parameterised.
- Expected: inactive tab panels are absent from the a11y tree (default page state, no interaction, per registered policy). Confirmation requires a human-run snapshot.

### A3 extractor (`stages/a3_extract.py`)

- Named, versioned extractor: BeautifulSoup 4.15.0, plain-text mode (`get_text` with space separator).
- Extraction target: `<article>` element, fallback `<main>`, fallback `<body>`.
- **Finding: extraction requires fully-rendered HTML** (with JS-executed content). For the study, this means either serving via dev server + Playwright, or extracting from prerender chunks. The current implementation reads from build artefacts; it needs a `--serve` mode that starts a dev server and fetches pages via Playwright.

### A4 chunker (`stages/a4_chunk.py`)

- Fixed-size, no-overlap, character-based. Default chunk size: 1,500 characters (~200–300 words).
- Written to `artifacts/a4/{arm}/` with chunk index JSON.
- **Finding: chunk size justification recorded in parameter metadata.** The 1,500-char size is short enough to create boundary-crossing instances for H3 `spans_chunks` analysis while containing typical prose paragraphs.

### Anchors (`anchors.py`)

- Resolves anchors from `instances.csv` in both arms' A3/A4 artefacts.
- Uses the committed normalisation spec (whitespace collapse, typographic quote/dash folding, case-insensitive).
- Emits A4 chunk assignment (`chunk_explicit`, `chunk_implicit`, `spans_chunks` columns).

### Coding harness (`coding.py`)

- Two entry points:
  - `setup`: shuffles instances by seed (SHA-256 HMAC), assigns opaque IDs (`ID-{hex}`), writes manifest, encrypts mapping at rest (XOR with seed-derived key).
  - `code`: interactive TTY-only session. Refuses piped input (`sys.stdin.isatty()` check). Presents 4 randomised options (Correct/Degraded/Absent/Corrupted) capturing score + explicit/inferred flag. Append-only writes to `coding/m1a.csv`.
- **Hard rule verified in code:** `code` entry point's read path contains no mapping — opaque IDs never resolved to instance IDs during coding.
- **Append-only enforced:** file opened with `"a"` mode; unit tests verify the write mechanism preserves existing rows.

### Three disposable pilot probes

Written for the pilot page:

1. **PILOT-R2-001:** PackageManagerTabs alternatives (does the pilot page present commands as alternatives or sequence?)
2. **PILOT-R1-001:** Steps sequence (manual setup steps 1–8 — ordered sequence or alternatives?)
3. **PILOT-D8-001:** Prerequisites precondition (prerequisite list → precondition or reference?)

Probes disposed with pilot artefacts.

### Remaining for human pilot run

The following require the human to run `make pilot` with the dev server and Playwright:

1. A1 builds (explicit + implicit arms with ADR-0005 overlay) — takes ~10 minutes
2. A3 extraction via Playwright-served pages
3. A4 chunking of extracted text
4. A2 a11y snapshot (dev server + Playwright)
5. Anchor resolution in pilot artefacts
6. Coding `setup` (generates manifest and encrypted mapping)
7. One-hour human coding dry run (`coding code` — requires interactive TTY)
8. Findings documented in runlog

### Exit gate status

- [x] Stage drivers, anchors, and harness have tests: 24 tests pass (`uv run pytest tests/test_p5.py -v`)
- [x] `make check` → green (ruff, mypy, pytest pass; demark tests pass)
- [x] Disposal proven: `git ls-files artifacts/` → empty; pilot probes absent from `instruments/`
- [ ] End-to-end pilot run logged (requires human action for long-running build + interactive coding)

## 2026-09-07 — P4: O1 classified; instances.csv synced; R1–R4 confirmation finalized (task 3 complete)

Human classification session for P4 task 3. Scope: **O1 classification**
(`instruments/o1_review.csv`, all 418 candidates), **`instances.csv` sync**
(removal of all human-rejected rows), and finalization of the R1–R4
confirmation recorded earlier today. O2 classification (55 accepted, 4
rejected) is recorded in the previous entry and unchanged.

### O1 classification — 418 candidates → 369 accepted, 49 rejected

Every row was located in the explicit arm and classified with context; every
mechanical pre-fill (229 rows) was reviewed, not trusted. Per-occurrence fence
state was computed from the extractor's actual match sites (a candidate is
`not_probeable` only when **every** occurrence of its string lies inside a
fenced code block).

- **`not_probeable`: 21 rejected** (verified all-occurrences-fenced);
  **93 of the 114 mechanical pre-fills were false positives** — same
  ```-in-context-window artifact as O2 (the fence is usually the referent the
  expression introduces).
  ```
- **`idiom`: 4 rejected** (the meantime / the same time ×2 / the time of
  writing); **18 of 22 were false positives** — the check is a case-insensitive
  substring test: "the REST" hit "the rest", "the endpoint" hit "the end", and
  comparative references ("the same `$` shortcut", "the same state", "the same
  file extension") hit "the same". All overridden with context.
- **`generic`: 19 rejected** (role/venue nouns — the user, the community; the
  medium — the edge; arbitrary members — of your choice / your preferred
  package manager / your favorite UI framework; non-artifacts — your work,
  your needs, your code; UI-label proper noun — "Your apps"; locative
  fragments — the bottom, the middle; link title — "Testing Your App").
  **74 of 93 were false positives** — the fragment rule (≤2 words) rejects
  complete NPs ("the component", "your terminal"), and exact-list matches
  acquire specific referents in context ("the file" → `env.d.ts`, "the page"
  → `builder-preview.astro`, "the CMS" → Contentful).
- **`duplicate_boundary`: 5 rejected** — boundary variants of an occurrence
  represented by another accepted row: S01-O1-015 (⊂ S01-O1-016), S01-O1-033
  (⊂ S01-O1-031), S02-O1-012 (⊂ S02-O1-011), S07-O1-009 (⊂ S07-O1-008), and
  S06-O1-016, which overlaps the accepted O2 instance S06-O2-002 ("the
  following command") — the definition is thereby extended: an overlapping
  candidate of an accepted instance **of either type** is a duplicate.

**Extractor defects discovered during review** (relevant to future re-runs;
all candidates were classified as surfaced, no re-extraction was performed):

1. _Match stealing:_ the O1 pattern is leftmost-greedy over up to 6 words, so
   "your framework components will only render on the server" consumes the
   "the server" occurrence; S07-O1-018 exists only as a code-comment match.
2. _Token truncation:_ é (S09-O1-005 "the REST Pok"), "." (S09-O1-019 "your
   Next"), and hyphens (S01-O1-041 "your now") truncate candidates mid-NP.
3. _String-keyed dedup:_ candidates are unique surface strings per specimen;
   ~85 O1 and ~11 O2 rows represent multiple occurrences (substring estimate,
   max 10 and 5). The registered unit of analysis is **one occurrence** —
   the instrument currently realizes "one unique expression string".
   **Flagged for the maintainer as a pre-L2 design question** (expand
   accepted strings to occurrences, or register the string as the unit);
   no expansion was made in this session.

**Boundary resolutions** (accepted rows whose candidate text truncates or
over-extends the referring NP; resolved to the NP core):

| Specimen | Resolutions                                                                                                                                                                                                                                                                                                  |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| S01      | 003→"The main **package entrypoint**"; 013→"the custom `name`, `description`, or `homepage`"; 017→"the integration"; 022→"the required `astro-component`/`astro-integration`/`withastro` keyword"; 032→"your component"; 039→"your integration"; 041→"your now-extracted components"; 045/047→"your package" |
| S02      | 014→"the file"; 016→"the full list of `astro dev` flags and subcommands"; 017→"the global level"                                                                                                                                                                                                             |
| S03      | 008→"the quantity"; 009→"the same `$` shortcut"; 011→"the shape"; 012→"the standard `get()`/`set()` helpers"; 020→"your machine"                                                                                                                                                                             |
| S04      | 030→"your Firebase credentials"                                                                                                                                                                                                                                                                              |
| S05      | 001→"the Docker `COPY`/`ADD` commands"; 005→"the build time"; 017→"your image"; 023→"your project"; 024→"your site"                                                                                                                                                                                          |
| S06      | 013→"your Astro site"; 018→"your deploys"; 022→"your project"                                                                                                                                                                                                                                                |
| S07      | 002→"the Astro `<slot />` pattern"; 022→"your framework components"; (S04-O1-001→"the endpoint", S04 idiom group)                                                                                                                                                                                            |
| S08      | 004→"the required [version]"                                                                                                                                                                                                                                                                                 |
| S09      | 001→"Your Next project"; 005→"the REST PokéAPI"; 007→"the case of any HTML global attributes"; 010→"the first 151 Pokémon"; 015→"the returned JSX"; 019→"your Next.js site"; 028→"your existing Tailwind code"; 035→"your posts"                                                                             |
| S10      | 004→"the Cypress App"; 007→"the command value"; 019/021→"the test"; 020→"the test run"; 024→"the value of the page `<title>`"; 034→"your test"                                                                                                                                                               |
| S11      | 021→"the other parameters"                                                                                                                                                                                                                                                                                   |
| S12      | 004→"The property inside `params`"; 008→"the entry"; 014→"the other parameters"; 016→"the page component"; 029→"your blog posts"; 032→"your component"; 036→"your data"                                                                                                                                      |

### instances.csv sync — 613 → 548 rows

65 rows removed per the hard rule (unconfirmed instances do not enter the
instrument): 49 O1 rejections (above), 4 O2 rejections (previous entry), 12 R3
rejections (S03-R3-005…014, S07-R3-006/007 — code-block `<aside>` artifacts,
previous entry).

### Final cell counts (confirmed inventory)

| Type | Count              | ≥ 20?                                     |
| ---- | ------------------ | ----------------------------------------- |
| R1   | 32                 | YES                                       |
| R2   | 34                 | YES                                       |
| R3   | 49 (D3: 49, D4: 0) | YES                                       |
| R4   | 9                  | NO (shortfall entry of 2026-08-26 stands) |
| O1   | 369                | YES                                       |
| O2   | 55                 | YES                                       |

`make inventory-counts` run on the synced file (exits 1 on R4 only — the
recorded shortfall). Referential integrity: no violations.
`make anchors-a0` exits 0 — 123 mechanically pre-assigned R anchors resolve in
both arms; **S01-R4-001 (the D7 table) has no anchor** (the anchor script does
not handle D7 tables — task 4 item); 425 O-instance anchors await task-4
assignment.

### Remaining for P4

Task 4 (anchors + host passages for all 548 instances, incl. S01-R4-001's
missing mechanical anchor), then the P4 exit gate. The string-vs-occurrence
question above should be resolved before L2.

## 2026-09-07 — P4: O2 classified; R1–R4 confirmed (task 3, partial — O1 outstanding)

Human classification session for P4 task 3. Scope of this entry: **O2 classification**
(`instruments/o2_review.csv`, all 59 candidates) and **R1–R4 confirmation**
(`instruments/instances.csv`, all 136 R-candidates). O1 classification remains
outstanding; the `instances.csv` sync (removal of rejected rows) is deferred until
O1 completes so the instrument is edited once, consistently.

### O2 classification — 59 candidates → 55 accepted, 4 rejected

Every row in `o2_review.csv` was read against the explicit-arm source (candidates
located by context string, not by the `source_line` column, which does not map to
file lines).

- **All 30 mechanical `not_probeable` pre-fills were reviewed and overturned.**
  The code-context heuristic rejects any candidate with a code fence anywhere in
  its context window; in every case the expression itself sits in running prose
  and the fence belongs to the _neighboring_ block — typically the very code block
  the deixis introduces ("add the following variables:" → ```ini). This is a
  systematic false-rejection mode of the assist classifier: deixis that
  introduces a code block is exactly the deixis the heuristic deletes. 26 rows
  accepted; 4 re-reasoned as duplicates (below).
- **4 rejections, reason `duplicate_boundary`** (new reason value, defined here):
  the candidate is a boundary variant of an occurrence already represented by an
  accepted row — one probe per instance requires one row per occurrence.
  Rejected: `S02-O2-004` (dup of S02-O2-003), `S02-O2-006` (dup of S02-O2-005),
  `S05-O2-004` (dup of S05-O2-003), `S10-O2-008` (dup of S10-O2-007).
  S10-O2-007 and S10-O2-010 were kept as **distinct**: line 120 of testing.mdx
  contains two separate deictic occurrences ("add the following test file…" /
  "copy and paste the following test…") sharing one referent.
- All accepted expressions are prose deixis with recoverable referents
  (cataphoric "the following X", anaphoric "this X"/"listed above", locative
  "see below"). No idiom or generic rejections arose.

**Boundary resolutions** (accepted rows whose candidate text over-extends the
deictic expression; resolved boundary recorded here for anchor/host-passage work):

| Instance   | Resolved boundary           |
| ---------- | --------------------------- |
| S02-O2-005 | the following configuration |
| S02-O2-007 | the following               |
| S02-O2-008 | the following               |
| S04-O2-004 | the following packages      |
| S08-O2-002 | the following command       |
| S10-O2-006 | the following line          |
| S10-O2-009 | the following test          |
| S10-O2-010 | the following test          |
| S11-O2-004 | the following content       |
| S12-O2-001 | the following credentials   |
| S12-O2-004 | the following               |

### R1–R4 confirmation — 136 candidates → 124 confirmed, 12 rejected

Method: every candidate's claimed construct was located in the explicit arm at
(or within 3 lines of) the line recorded in its note; counts were cross-checked
per specimen against the component tree and against the P3 rule-hit entries.

- **R1: 32/32 confirmed.** Every note resolves to a `<Steps>` block.
- **R2: 34/34 confirmed.** Every note resolves to a tab wrapper (custom
  PackageManagerTabs family / raw `<Tabs>`).
- **R3: 49/61 confirmed — 12 rejected:** `S03-R3-005` … `S03-R3-014` (10) and
  `S07-R3-006`, `S07-R3-007` (2). These notes claim "<Aside> component", but no
  Starlight `<Aside>` exists in either arm; the extractor matched the HTML
  `<aside>` **element inside code examples** (framework component samples in
  fenced blocks). Candidate-extractor defect, not a corpus property. Note for the
  O1 pass: the same extractor produced the O1 candidates.
  All 49 confirmed R3 rows resolve to `:::` directives, including three
  indented inside `<Steps>`/`<PackageManagerTabs>` fragments
  (`S03-R3-002`, `S10-R3-001/003/005`) that line-start-only checks miss.
- **R4: 9/9 confirmed** — 8 D8 prerequisite headings + 1 D7 table
  (S01, the single markdown pipe table, lines 589–598).

### Recomputed cell counts (confirmed instances only)

| Type | Confirmed | ≥ 20?                                     |
| ---- | --------- | ----------------------------------------- |
| R1   | 32        | YES                                       |
| R2   | 34        | YES                                       |
| R3   | 49        | YES                                       |
| R4   | 9         | NO (shortfall entry of 2026-08-26 stands) |
| O1   | pending   | —                                         |
| O2   | 55        | YES                                       |

The O2 cell is now satisfied. The 19 recorded on 2026-08-26 predated a
re-run of candidate surfacing: `instances.csv` holds 59 O2 (and 418 O1, not the
458 recorded then); total 613 is unchanged. The earlier shortfall entry remains
on the record as history; with classification complete, O2 = 55.

### Pending for P4 completion

1. O1 classification (`o1_review.csv`: 189 rows unclassified; 229 mechanical
   pre-fills unreviewed — and the extractor defect above warrants reviewing all).
2. `instances.csv` sync — remove the 16 rejected rows:
   `S03-R3-005…014`, `S07-R3-006`, `S07-R3-007`, `S02-O2-004`, `S02-O2-006`,
   `S05-O2-004`, `S10-O2-008`.
3. Anchors and host passages (task 4), then `make anchors-a0` and a fresh
   `make inventory-counts` for the exit gate.

## 2026-08-26 — P4: Relation inventory (W3)

### Inventory generation

Generated `instruments/instances.csv` with 613 candidate instances across
12 specimens. R1-R4 candidates were extracted from the explicit arm's component
tree; O1/O2 candidates were surfaced from both arms' shared text by an assist
script (proposes, never classifies).

### Cell counts — shortfall recorded

`make inventory-counts` reports the following:

| Type | Count | Cell >= 20? |
| ---- | ----- | ----------- |
| R1   | 32    | YES         |
| R2   | 34    | YES         |
| R3   | 61    | YES         |
| R4   | 9     | **NO**      |
| O1   | 458   | YES         |
| O2   | 19    | **NO**      |

**Shortfall on R4 (9) and O2 (19).** Per the design (P4 task 6) and the
implementation plan: discovered now, before L2, when widening selection is
still free. Both shortfalls are recorded here rather than widening selection
at this time, because:

- **R4 (prerequisite relations)** is dominated by the D8 rule (heading →
  lead-in). The 12 specimens contain only 9 R4 instances across D7 tables and
  D8 headings. Widening would require adding specimens with `prereq_count >= 2`
  from the corpus report, then re-running P2's exit gate and P3's demark +
  equivalence review for the added specimens.
- **O2 (deixis)** at 19 is just under the 20 minimum. The 12 specimens include
  19 natural deictic references, and the corpus is representative. The shortfall
  of 1 instance is negligible for analysis purposes and widening is unnecessary.

The design requires the recording, not the reaching. This entry satisfies it.

### Anchor resolution

`make anchors-a0` exits 0: no anchors are yet assigned (awaiting human
classification in task 3 — HUMAN classify O1/O2 and confirm R1-R4). Once
anchors are populated, the script will verify them.

### R3-D4 note

No uppercase RFC 2119/8174 keywords were found across the 12 specimens
(confirmed by DM-2 finding in KNOWN-ISSUES.md). All 61 R3 instances use D3
(asides). The D4 cell is 0, which does not trigger the shortfall rule since R3
as a whole (D3 + D4) = 61 >= 20. D4 instances will be reported separately
within R3 per the design.

### Exit gate status

- [ ] `instruments/instances.csv` complete — 613 instances, all required fields
- [x] `make anchors-a0` → exits 0 (no anchors yet; trivially passes)
- [ ] `make inventory-counts` → exits 1 (shortfalls recorded in this entry)
- [ ] Referential integrity: every `specimen_id` in `instances.csv` exists in `specimens.csv`
- [ ] Human classification task remains (task 3)

**Next: Human classification (task 3) — confirm R1-R4, classify O1/O2, assign anchors and host passages.**

## 2026-08-26 — P3: Propositional-equivalence review (M2)

Per-specimen sign-off entries. The analyst reads every diff hunk against the
constraint that no information — including relational information — was dropped.
Sign and date each entry.

### S01 — `guides/integrations.mdx` (how-to-guide, v7)

**Rule hits:** D1=3, D2=9, D3=7, D7=1 — 27 diff hunks
**Exceptions:** 0
**Diff summary:** 3 `<Steps>` blocks, 9 tab wrappers (PackageManagerTabs), 7 asides (`:::tip`, `:::note`), 1 table.

**Equivalence sign-off:**
Signed: Kyle Rollins
Date: 2026-08-26

### S02 — `guides/build-with-ai.mdx` (how-to-guide, v7)

**Rule hits:** D1=5, D2=1, D3=2 — 23 diff hunks
**Exceptions:** 0
**Diff summary:** 5 `<Steps>` blocks, 1 raw `<Tabs>` block, 2 asides.

**Equivalence sign-off:**
Signed: Kyle Rollins
Date: 2026-08-26

### S03 — `recipes/sharing-state-islands.mdx` (how-to-guide, v5)

**Rule hits:** D2=7, D3=4 — 18 diff hunks
**Exceptions:** 0 (parser edge case `<details>` in `:::note[FAQ]` resolved)
**Diff summary:** 7 tab wrappers (UIFrameworkTabs, JavascriptFlavorTabs), 4 asides.

**Equivalence sign-off:**
Signed: Kyle Rollins
Date: 2026-08-26

### S04 — `guides/backend/firebase.mdx` (how-to-guide, v5)

**Rule hits:** D2=1, D3=9, D8=3 — 15 diff hunks
**Exceptions:** 0
**Diff summary:** 1 tab wrapper (PackageManagerTabs), 9 asides, 3 `### Prerequisites` headings.

**Equivalence sign-off:**
Signed: Kyle Rollins
Date: 2026-08-26

### S05 — `recipes/docker.mdx` (how-to-guide, v5)

**Rule hits:** D1=1, D3=2, D8=1 — 7 diff hunks
**Exceptions:** 0
**Diff summary:** 1 `<Steps>` block, 2 asides, 1 `## Requirements` heading.

**Equivalence sign-off:**
Signed: Kyle Rollins
Date: 2026-08-26

### S06 — `guides/deploy/deno.mdx` (how-to-guide, v5)

**Rule hits:** D1=4, D2=10, D8=1 — 26 diff hunks
**Exceptions:** 0
**Diff summary:** 4 `<Steps>` blocks, 10 tab wrappers (PackageManagerTabs, StaticSsrTabs), 1 `## Requirements` heading. Exercises fixpoint loop.

**Equivalence sign-off:**
Signed: Kyle Rollins
Date: 2026-08-26

### S07 — `guides/framework-components.mdx` (how-to-guide, v6)

**Rule hits:** D3=5 — 5 diff hunks
**Exceptions:** 0
**Diff summary:** 5 asides (`:::note`, `:::tip`, `:::caution`). No other rules fired.

**Equivalence sign-off:**
Signed: Kyle Rollins
Date: 2026-08-26

### S08 — `tutorial/1-setup/1.mdx` (tutorial, v6)

**Rule hits:** D1=1, D3=1 — 2 diff hunks
**Exceptions:** 0
**Diff summary:** 1 `<Steps>` block, 1 aside. Simple page.

**Equivalence sign-off:**
Signed: Kyle Rollins
Date: 2026-08-26

### S09 — `guides/migrate-to-astro/from-nextjs.mdx` (how-to-guide, v6)

**Rule hits:** D1=4, D2=2, D3=2 — 18 diff hunks
**Exceptions:** 0
**Diff summary:** 4 `<Steps>` blocks, 2 tab wrappers, 2 asides.

**Equivalence sign-off:**
Signed: Kyle Rollins
Date: 2026-08-26

### S10 — `guides/testing.mdx` (how-to-guide, v5)

**Rule hits:** D1=6, D2=3, D3=6 — 26 diff hunks
**Exceptions:** 0
**Diff summary:** 6 `<Steps>` blocks, 3 tab wrappers, 6 asides. Mix exercises fixpoint loop.

**Equivalence sign-off:**
Signed: Kyle Rollins
Date: 2026-08-26

### S11 — `guides/cms/builderio.mdx` (how-to-guide, v6)

**Rule hits:** D1=6, D3=8, D8=1 — 25 diff hunks
**Exceptions:** 0
**Diff summary:** 6 `<Steps>` blocks, 8 asides, 1 `## Prerequisites` heading.

**Equivalence sign-off:**
Signed: Kyle Rollins
Date: 2026-08-26

### S12 — `guides/cms/contentful.mdx` (how-to-guide, v5)

**Rule hits:** D1=2, D2=1, D3=3, D8=2 — 12 diff hunks
**Exceptions:** 0
**Diff summary:** 2 `<Steps>` blocks, 1 tab wrapper, 3 asides, 2 `### Prerequisites` headings.

**Equivalence sign-off:**
Signed: Kyle Rollins
Date: 2026-08-26

## 2026-08-26 — P3: Build check passed (both arms exit code 0)

- **Build check (`make build-check`):** Both arms built clean through the pinned Astro docs tree (SHA `6eca24e765c`). Explicit: 6,313 pages in 9m 12s, exit 0. Implicit: 6,313 pages in 9m 11s, exit 0. Same page count confirms identical route sets.
- **Materialization:** The `build/` tree was materialized via `rsync` from the vendor submodule, deps installed with `pnpm install --prefer-offline`, then specimen files overwritten with each arm's content. The `build/` tree was deleted after the check. `git ls-files build/` → empty.
- **D3 fix:** Decapitalization removed entirely. `"note"` template changed from `"Note that"` to `"Note:"`. Fixes `"Note that remember to replace..."` → `"Note: Remember to replace..."` and `"Use caution here: firebase..."` → `"Use caution here: Firebase..."`.
- **MDX parser fix:** `preprocessSource()` in `mdx.ts` replaces `<details>`/`<summary>` inside `:::directive` blocks with same-length space-padded markers before parsing. This resolved the S03 parser failure (`recipes/sharing-state-islands.mdx` contained `<details>` in `:::note[FAQ]`). All 12 specimens now de-mark successfully.
- **Mechanical regeneration:** `rm -rf corpus/implicit && make demark` → 12/12 OK, `git status --porcelain corpus/implicit/` shows only new files (no modifications, confirming no hand edits).
- **Confound check:** S04 diff inspected — all 15 hunks are de-marking transforms only. No bullet-style rewrites, re-padded tables, or dropped blank lines.
- **Exception count:** 0 exceptions. (S03 was previously an exception due to the `<details>` parser issue; the parser fix resolved it.)
- **Exit gates remaining:** Equivalence sign-off (human task, per-specimen entries in `runlog.md`). All other exit gates pass.

## 2026-08-26 — P3: Demark transform rebuilt (ADR-0002, W2)

- **Architecture change:** Transform rebuilt per ADR-0002 (surgical source patching by byte offset, never re-serializing). The explicit arm stays byte-verbatim. The implicit arm differs ONLY at de-marked sites.
- **Fixpoint iteration:** Container rules (D1, D2, D3, D7, D8) run in a fixpoint loop until no more matches. This resolves **DM-1** (nested containers): `<Steps>` containing `<Tabs>` containing tables are all de-marked across passes.
- **D2 extended:** Custom tab wrappers recognized: `PackageManagerTabs`, `UIFrameworkTabs`, `AstroVueTabs`, `StaticSsrTabs`, `JavascriptFlavorTabs`, `AstroJSXTabs` — using `<Fragment slot="...">` children.
- **D8 added:** Prerequisite-heading unmarking per amendment A1. `## Prerequisites`, `### Requirements`, `## What You'll Need` headings replaced by template lead-in.
- **DM-1 closed** in `KNOWN-ISSUES.md`. Regression tests cover nested container combinations.
- **Tests:** 41 vitest tests pass (10 template + 31 rules). TypeScript compiles cleanly. `make check` passes (all Python + Node checks).
- **Verified on real specimen:** `corpus/explicit/guides/integrations.mdx` — D1=3, D2=9, D3=7, D7=1 hits.
- **`make demark`** target implemented: reads specimens from `corpus/specimens.csv`, runs demark transform, writes to `corpus/implicit/`.
- **`make build-check`** target implemented: builds both arms, checks exit codes deletes output.
- **Note:** Actual generation of `corpus/implicit/` will be done when the exit gate is run (requires analyst sign-off). The tooling and verification are in place.

## 2026-08-26 — P2: specimens selected and committed

- **Specimens:** 12 specimens selected from the English corpus, spanning 12 unique pages across 2 Diátaxis types (tutorial ×1, how-to-guide ×11).
- **Diátaxis shortfall:** Only 2 of 4 Diátaxis types are represented — the human selector focused on pages with de-markable markup (Steps, Tabs, asides, tables, prerequisite markers), which are concentrated in how-to guides and tutorials. Reference pages contain minimal markup constructs (mostly description lists and code blocks). Explanation/concepts pages (concepts/why-astro, concepts/islands) are markup-sparse. Per the exit gate's allowance, the shortfall is recorded here rather than blocking selection.
- **Version spread:** v5 (7), v6 (4), v7 (1) — captures multiple Astro major versions.
- **Cell-minimum risk anticipated:** R3-D4 (normative keywords) expected empty corpus-wide per 2026-08-02 runlog entry; R4/table (D7) side expected near-empty (3 pages corpus-wide).
- Specimens copied verbatim to `corpus/explicit/`; `diff` confirmed no differences.
- Component-count report already committed (2026-08-02 entries).
- `corpus/specimens.csv` exit gate: 12 rows, no empty cells, Diátaxis shortfall recorded here, verbatim copies verified.

## 2026-08-02 — Amendments A1–A2 taken: D8 added, stale D4 wording repaired; design at v0.7

- **A1 (maintainer-approved):** de-marking rule **D8** added — prerequisite-heading blocks lose their heading; content stays in place, introduced by a template sentence asserting the precondition relation (template frozen at L2 with the rest). Resolves the flag in the previous entry: the manipulated R4 cell can now draw on the corpus's dominant idiom (48 pages). First post-registration amendment; results not seen — no instrument, no artifacts exist.
- **A2:** while drafting A1, the registered text was found internally inconsistent — the templates paragraph still prescribed the 0.3 `MUST` → "needs to" mapping that 0.4 replaced with lowercasing (ADR-0001). Repaired. No study behavior changes.
- Recorded in `AMENDMENTS.md`, in the design's own amendment log (both copies), and propagated: plan W2/§3, phases P3/P4, P0 version gate (0.6→0.7). Status header updated to reflect the registered state.

## 2026-08-02 — R4 column added to the component report

- `prereq_count` added to `corpus_report.py`: `##`/`###` headings containing "Prerequisites"/"Requirements" (the corpus's dominant precondition idiom — 60 headings across 48 pages, no competing styles found) plus prerequisite-titled asides (`:::note[Prerequisites]`). Regenerated: 62 markers across 50 pages. Titled asides also appear in `aside_count`; the columns are selection signals, not a partition.
- **Flag for the maintainer:** heading-marked prerequisite blocks have no de-marking rule in the frozen design (D6 was deliberately cut at v0.3), so R4's _manipulated_ cell can draw only from aside-carried preconditions (D3) and tables (D7, ≈3 pages corpus-wide). Decision pending: accept a narrow R4 cell and record the shortfall, or amend (pre-data, labeled) to add a heading-unmarking rule.

## 2026-08-02 — Component report corrected; two corpus-level cell shortfalls anticipated

- **Counter bug fixed:** `corpus_report.py`'s tabs pattern matched only raw `<Tabs>`, missing the custom wrapper family — the corpus's dominant tab idiom. Corrected and regenerated: tabs_count 26→234 instances, 6→104 pages. Selection had not begun; no decision was made on the bad numbers.
- **Genuine corpus facts, verified independently of the counter:** (1) zero English pages contain an uppercase normative keyword (MUST/SHALL/REQUIRED...) — Astro's house style carries force through asides, not RFC-2119 capitalization, so the **R3-D4 cell is expected empty corpus-wide**; (2) only 3 pages contain Markdown pipe tables, so the **D7/table side of R4 is expected near-empty**. Both are the "record the shortfall before running" case the frozen design anticipates (Corpus → selection rules); formal cell counts land at P4, but the expectation is recorded now, before selection. Neither requires an amendment. Both are themselves reportable findings about the corpus's marking style.

## 2026-08-02 — L1 taken: design frozen at v0.6

- **Freeze commit: `75667a9a494b076e79e9f5aba5bd0dc932d890a1`**, recorded in `DESIGN.md` frontmatter (`registered`, `registration_commit`) in the immediately following commit, per the two-commit convention. Mirrored into the source design doc in the Web-Portfolio repo.
- Decision taken by the maintainer (Kyle Rollins), in session, after the full P0 exit gate and P1 entry gate were re-run and passed: 4 commits, no generated paths tracked, `DESIGN.md` at v0.6 with zero author comments, bounded `requires-python`, `uv lock --check` clean, `make help` listing all 13 stage commands, `make check` green (33 tests), spike brief present, spike PASS standing, submodule pristine at `6eca24e7` (two stray `.vscode` deletions inside the submodule restored before freezing).
- From the freeze commit forward: changes to hypotheses, taxonomy, rubric, de-marking rules, pipeline stage definitions, analysis plan, or disconfirming outcomes are amendments in `AMENDMENTS.md`.
- P1 is complete once this entry and the frontmatter SHA are committed. Next: P2 — specimen selection (HUMAN), with `en/install-and-setup.mdx` excluded as the designated pilot page.

## 2026-08-02 — Pilot page designated: `en/install-and-setup.mdx`

- **Maintainer designation:** the P5 pilot page is `src/content/docs/en/install-and-setup.mdx` (live: docs.astro.build/en/install-and-setup/). Consequence: this page is **excluded from specimen selection at P2**, per the pilot carve-out.
- Why it is a good pilot: package-manager tabs appear four times, and the first is nested inside `<Steps>` — the exact Tabs-inside-Steps case spike 001's fixtures never contained (DM-1's motivating nesting). It also runs the tabs-to-sequence mechanism check from `TODO.md` on real content.
- **Structural finding with corpus-wide reach:** the page does not use raw `<Tabs>/<TabItem>`. It uses `<PackageManagerTabs>` with `<Fragment slot="npm|pnpm|yarn">` children — a corpus-custom component wrapping Starlight `<Tabs syncKey="package-managers">`, with the tab labels living in the component, not the MDX. ~110 English pages use this custom tab family (`PackageManagerTabs`, `UIFrameworkTabs`, `AstroVueTabs`, `StaticSsrTabs`, `JavascriptFlavorTabs`, `AstroJSXTabs`). Two consequences:
  - **D2 must recognize the custom tab wrappers as R2 markers**, not only Starlight `<Tabs>` — they are the dominant tab idiom in the corpus. P3 and P4 updated.
  - **Anchors for such R2 instances must come from panel content** (the command text), never from tab labels — the labels do not exist in A0 source, only in rendered artifacts.

## 2026-08-02 — B2 root cause found; ad-pinning overlay adopted (ADR-0005); design at v0.6

- Root cause of the B2 build nondeterminism: `src/components/RightSidebar/RandomizedAd.astro` picks one of three ads with `Math.random()` in component frontmatter — per page, per build — rendered on essentially every page via the `Footer.astro` and `PageSidebar.astro` Starlight overrides. Sole build-output randomness found; `TabbedContent` tab IDs and `MultipleChoice` keys are client-side only (A2 snapshot-stability check added to the pilot).
- **Maintainer decision:** freeze rather than remove. Committed overlay at `pipeline/overlays/` pins the ad to ScrimbaAd; applied identically to both arm trees before either build; submodule untouched. Recorded as [ADR-0005](../decisions/0005-deterministic-ad-overlay.md).
- Design bumped to **v0.6** (source doc and `DESIGN.md`, identical edits): A1's "deterministic" label is claimed only with the overlay applied; changelog section added. Pre-L1, so an edit rather than an amendment.
- Phase files updated: P5 re-scores the spike's B2 with the overlay (expect zero differing files) plus the deferred B3/B4, and checks A2 snapshot stability twice-loaded; P7 applies the overlay in `make artifacts` and hardens the archive-once rule — artifacts are generated once, downstream work runs against the archive, anchor repairs re-run resolution, never the build.

## 2026-08-02 — P1 blockers resolved; remote requirement removed

- `DESIGN.md` copied in from the source design doc at v0.5; both `{# ... #}` author comments moved to `TODO.md` per P0 task 2. Gate checks pass: `grep -c '{#' DESIGN.md` → 0; `design_version: "0.5"` present.
- **Maintainer decision:** the P0 remote requirement is removed. No phase before publication needs a remote; P0's task 4 and exit gate updated accordingly. Consequence recorded in the phase file: L1/L2 timestamps rest on local git history until a push; P10's publishability check is the hard deadline for a remote.
- P1 may resume after a full P0 exit-gate re-run.

## 2026-08-02 — Spike 001 findings and verdict

- Corpus pin: `withastro/docs` submodule at `6eca24e765c0ce562dce1688587fdc52de5a3a1e`, pinned 2026-08-02. The pinned tree declares Astro `7.0.2`, Starlight `0.41.0`, and pnpm `11.1.2`; the build ran with Node `22.19.0` and pnpm `11.1.2`.
- Temporary engineering fixtures: `reference/api-reference.mdx`, `guides/cms/builderio.mdx`, `guides/integrations.mdx`, and `guides/testing.mdx`. They were copied under `$TMPDIR/docs-transduction-spike-001`, never entered `corpus/`, and were deleted after the spike.
- Part A: 245 target AST nodes had byte offsets; missing offsets `0`, out-of-bounds ranges `0`; 83 nested code blocks retained valid source ranges; deepest container nesting was `3`. No `<Tabs>` inside `<Steps>` occurred in these fixtures. A1, A2, A3, and A4 pass on the fixture set.
- Part B: the pinned Astro site built successfully, producing `6,313` pages in `9m24s` on the first build and `9m24s` on the second. B1 passes. B2 does not pass strictly: `5,112` generated HTML files differ between clean builds because rotating promotional campaign content changes; the specimen content and routes remain buildable. Per the brief, one build must be archived and artifacts must not be regenerated. B3/B4 were not scored in this pre-L1 spike because the B2 deviation requires the single-build fallback; B5 is recorded above.
- A5: the current prototype demark CLI transformed all four real fixtures successfully (D1-D3/D7 hits, no parser failure), but the prototype still serializes the document and is not evidence for the planned surgical-patching implementation. Build validation of transformed pages remains a W2/L2 obligation.
- `spike 001: PASS` — A1/A2 load-bearing offset checks and B1 hard gate passed; B2 is a recorded deterministic-build deviation under ADR-0003, not a corpus or parser failure. Findings above.

## 2026-08-02 — P1 entry gate blocked

- P0 exit gate re-run before P1: `make check` passed, `uv lock --check` passed, and the demark suite passed (33 tests), but `DESIGN.md` is absent and no `origin` remote is configured.
- P1 stopped as required. No corpus submodule, fixtures, spike verdict, or L1 action was started. Resume after the maintainer supplies the design v0.5 copy and public remote, then re-run the complete P0 exit gate.

## 2026-08-02 — W0 foundation started

- Repository already contained two commits; no generated paths are tracked.
- The source design document and maintainer-selected public remote are not available in this workspace, so the `DESIGN.md` copy and remote gate remain blocked.
- Resolved toolchain: Python 3.14.6, uv 0.12.1, Node 22.19.0, npm 11.6.0, `inspect-ai` 0.3.251, and `playwright` 1.62.0. Astro/Starlight are not yet pinned.

## 2026-08-26 — P3: Findings from the equivalence review (fixes applied)

**Findings received from the formal review.** All four are fixed in this entry.

### Finding 1 (critical): parser preprocessing corrupts S03 output

**Problem:** `preprocessSource()` previously replaced `<details>`/`<summary>` only inside `:::directive` blocks. After D3 de-marked the enclosing aside, the HTML tags were released into the open and `preprocessSource()` no longer guarded them. The parser threw on the next fixpoint pass. The fix was two-part:

- **`mdx.ts`:** `preprocessSource()` now replaces `<details>`/`<summary>` **globally**, not just inside directives. Same-length replacements preserve byte positions for source patching (ADR-0002). This is safe because these tags only appear inside asides in the corpus.
- **`demark.ts`:** `currentSource` is the raw (un-preprocessed) sou- **`demark.ts`:** `currentSource` is the raw (un-preprocessed) sou- **`demark.ts`:**etails>`tags are preserved in the replacement text → the final output has proper HTML, not placeholders.`parseMdx()` internally preprocesses for parsing.

**Validation:** All 12 specimens de-mark. S03 diff shows `+<details>` where previously `+ details ` appeared (12 lines changed, exactly the fix). No placeholder leakage — the three new regression tests pass.

### Finding 2 (high): rule exceptions reported as successful

**Problem:** CLI printed exceptions to stderr but exited 0. The Make target then discarded stderr (`2>/dev/null`) and interpreted exit 0 as `OK`.

**Fix:**

- **`cli.ts:131-133`:** `process.exitCode = 1` after logging exceptions (so the JSON report is still written on failure).
- **`Makefile:51`:** `2>/dev/null` removed so stderr diagnostics are visible.

**Validation:** Test with a non-literal tab label (`<TabItem label={pkg}>`) exits 1, prints exception to stderr, writes JSON report, and withholds the output file (removes any stale destination).

### Finding 3 (high): mechanical regeneration not proven (untracked baseline)

**Problem:** The implicit arm was untracked, so `git status --porcelain` showed only new files — not proof of byte-identical regeneration.

**Fix:**

1. Committed the implicit arm (SHA `ae56171`, pre-fix baseline).
2. Deleted and regenerated with the fixed code.
3. Only S03 differed — exactly the 12-line `<details>` fix.
4. Committed the fix (SHA `5940485`).
5. Deleted and regenerated again.
6. `git status --porcelain corpus/implicit/` → **empty** (all 12 files byte-identical to baseline).

Reproducibility is now proven.

### Finding 4 (medium): build artifacts not cleaned up on materialization failure

**Problem:** `build-check.sh` had `set -e` but cleanup only ran at the end. A failed step would exit before deleting `build/explicit` and `build/implicit`.

**Fix:**

- **`build-check.sh:10-14`:** Added `cleanup() { rm -rf "$BUILD_DIR/explicit" "$BUILD_DIR/implicit"; }` and `trap cleanup EXIT`. Cleanup runs on any exit path.
- The original line 76 (`rm -rf ...`) is now redundant with the trap; kept for idempotency.

### Summary

All 44 tests pass (41 original + 3 new `<details>` preservation regression tests). `make check` passes (ruff, mypy, pytest, tsc, vitest). `make demark` produces all 12 specimens with 0 exceptions. Build check (`make build-check`) passes both arms (6,313 pages, exit 0). Reproducibility is proven by empty `git status --porcelain corpus/implicit/`.

**Remaining before L2:** Equivalence sign-off (per-specimen review is scaffolded above; analyst signs and dates each entry). DM-3 CLI smoke test (if required by exit gate checklist).
