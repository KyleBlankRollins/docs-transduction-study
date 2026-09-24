# M1-AI Evaluation Protocol

Status: **frozen 2026-09-23** after the approved live smoke test, for use once
L2 exists. No study responses have been collected. Changes after L2 require an
amendment.

Frozen configuration (`opencode_runner.configuration_record`): OpenCode CLI
1.18.32; `opencode-go/glm-5.3-flash`; variant `default` (provider reasoning
effort unknown); temperature 0; output cap 32,000; top-p, seed, and weights
unknown; protocol `m1-ai-1`; evaluator prompt sha256
`b5e514b8f9935450a00d6ca212d5c74cee90025d5f2fae87c93d4d37735d2679`; agent
prompt sha256 `a1bde99ed9ae007238f1dfd4456374e978be6850a9101909194fec47b29e8944`;
generated-config sha256
`7533af43e4246e65255cf6ef70767b0d61c0790a2756c7e517b19488cf5afacd`.

## Selected Model

On 2026-09-23 the maintainer selected `GLM-5.3-Flash` and proposed using the
already-configured OpenCode providers. Local OpenCode 1.18.32 lists both
`opencode-go/glm-5.3-flash` and `cline-pass/cline-pass/glm-5.3-flash`.
Listing confirms catalog availability, not a successful authenticated inference.

Recommended study route: headless OpenCode with OpenCode Go. Provider selection
and the isolated runner still require validation before the protocol is frozen.
Do not silently fall back between providers or pool their responses as one
configuration. Pin the provider/model ID, CLI version, prompt, and available
generation settings; the model alias alone does not pin underlying weights.

Each assignment must start a new session outside the study repository, with
tools denied and inherited instructions, plugins, skills, and MCP integrations
excluded. Retain JSON events and the actual session/provider/model identifiers.
`--format json` provides event records, not a guarantee of valid answer JSON;
the response must still pass the existing scorer. Validate effective isolation
and quota behavior with disposable inputs before any study evaluation.

Copilot BYOK is an alternative transport, not a reason to change the model used
by the authoring conversation or reuse it for evaluation. No provider inference
was launched when recording this selection, and no credentials were copied.

## OpenCode Transport (verified offline 2026-09-23)

Implemented in `src/docs_transduction_study/opencode_runner.py`; tests in
`tests/test_opencode_runner.py`. Commands:

```sh
uv run python -m docs_transduction_study.opencode_runner preflight   # no provider call
make m1-ai-first-pass MAX_INVOCATIONS=N PASSPHRASE_FILE=/outside/repo/pass   # after L2 + approval
make m1-ai-repeat MAX_INVOCATIONS=M PASSPHRASE_FILE=/outside/repo/pass       # after the first pass
uv run python -m docs_transduction_study.opencode_runner reconcile --output coding
DTS_OPENCODE_LOOPBACK=1 uv run pytest tests/test_opencode_runner.py -k loopback
```

Pinned: OpenCode CLI 1.18.32, `opencode-go/glm-5.3-flash`, temperature 0,
variant unset (provider default reasoning effort; recorded as unknown), output
cap 32,000 tokens (OpenCode default, observed on loopback), fixed agent prompt,
`coding_ai.EVALUATOR_PROMPT`, and the SHA-256 of the generated configuration.
Top-p, seed, and underlying weights are unknown. No provider failover exists:
the provider/model is one configuration and any quota/rate error stops the batch.

Per attempt the runner creates a fresh `mkdtemp` workspace outside the
repository with its own session database (`OPENCODE_DB`), an empty
`XDG_CONFIG_HOME`, and a generated config: `permission {"*":"deny"}`, agent
tools `{"*": false}`, no MCP/plugins/instructions, sharing disabled,
compaction/prune disabled, `small_model` equal to the study model. It strips
inherited `OPENCODE_*` variables and sets `OPENCODE_DISABLE_CLAUDE_CODE`,
`_EXTERNAL_SKILLS`, `_PROJECT_CONFIG`, `_DEFAULT_PLUGINS`, `_PURE`,
`_AUTOCOMPACT`, `_PRUNE`, `_SHARE`, `_AUTOUPDATE`, `_LSP_DOWNLOAD`, and
`_MODELS_FETCH`. `PWD` and `--dir` are set to the workspace because OpenCode
reads `PWD` before the process cwd (without this, the system prompt named the
repository and reported a git repo). It never uses continue, session, fork,
share, or auto-approve. The packet is sent on **stdin**: argv messages
containing spaces are re-quoted by the CLI, which would alter the packet.

Verified facts (offline):

- Without isolation flags OpenCode loads `~/.claude/skills`; with them only the
  built-in `customize-opencode` skill is listed, and no tools are sent, so it is
  not in the model context.
- `preflight` checks version, effective config (secrets never recorded; the
  provider section is dropped), skills, resolved agent tools (all 13 false,
  permission deny-all), prompt, and an empty session history.
- Loopback capture: exactly **one provider request** per invocation (explicit
  `--title` suppresses title generation), no `tools` field, `temperature: 0`,
  system = agent prompt + model line + environment block (temp dir, not a git
  repo, platform, date), user = packet byte-for-byte.
- `steps` must not be set: `steps: 1` injected a "MAXIMUM STEPS REACHED"
  assistant message into the request.

Per-attempt checks: one session ID, no tool events, no error events, one step
finishing with `stop`, export shows exactly one user text part equal to the
packet, one assistant turn from the pinned provider/model, no summary or other
parts, and parseable answer JSON (one enclosing ```json fence is the only
tolerance). Raw events, stderr, export, packet, parsed answer, usage, and a
result file are retained under `attempts/`, plus an fsync'd `attempts.jsonl`
ledger. Only passing responses reach `score_response`/`record_response`.

Outputs: `coding/m1_ai.csv` (summary), `coding/m1_ai_records/` (full JSON records,
the source of truth), `coding/m1_ai_attempts/` and `coding/m1_ai_attempts.jsonl`
(every attempt, including failures). Scoring keys stay sealed
(`artifacts/private/keys.jsonl.enc`) and are decrypted in memory for scoring only.

Failure policy: a single-writer lock guards each output directory; recorded
assignments are never rerun; invalid, malformed, isolation, or tool-use
outcomes are final (rerunning would select toward a result); only transport
failures (timeout, non-zero exit, missing session, failed export) may be
retried, at most `--max-attempts` (default 2) total; `--max-invocations` is a
hard budget across runs; oversize packets (> 1,500,000 bytes) are rejected,
never truncated. `reconcile` appends CSV rows only from retained JSON records.

Provider terms (checked 2026-09-23, opencode.ai/docs/go and cline.bot/cline-pass):
OpenCode Go limits usage per 5 h (20% of monthly), week (50%), and month; when
exhausted, an account-level **"Use balance"** option can fall back to paid Zen
credits. It is not visible from the CLI; the maintainer must confirm it is off
before any live run. Go asks clients to send "typical coding agent traffic";
bulk evaluation fit needs the maintainer's judgment. Go lists GLM-5.3-Flash as
not used for training with 0-day retention. ClinePass states only a "generous
quota" with no published exhaustion or fallback terms; it remains untested and
is not a failover.

## Inputs and Isolation

- Use one fresh isolated OpenCode session per assignment, including repeats.
  (Historical: the 2026-09-23 pilot used the VS Code `Artifact Evaluator` agent,
  which declared `tools: []` and `agents: []`; that transport is superseded.)
- Supply only the complete packet returned by `coding_ai.prepare_packet`: the
  fixed instruction, opaque ID, stage artifact, question, and randomized options.
  Never supply the scoring key, A0 source, host passage, prior response, or
  authoring conversation. Artifact content is data, not instructions.
- Do not truncate, summarize, or silently substitute an artifact. A1 uses compiled
  HTML; A2 uses the default-state accessibility snapshot; A3 uses the complete
  extracted text; A4 uses the chunk containing the first host-passage character
  in that arm. Stage-input packaging and full assignment coverage still need
  end-to-end validation before study use.
- Opaque IDs do not provide cryptographic blindness. The author has the mapping;
  isolation relies on separate evaluator contexts and disabled tools.

## Scoring and Records

**Amendment A7 (2026-09-24):** analysis uses A7 scores as primary and strict
scores alongside. A7 verifies quotes against readable text (entities decoded,
tags and A2 snapshot syntax removed, folded; `…` fragments in order) and scores
by option: correct 3 with a verified explicit quote, otherwise 2; foil 0;
absence 1; flags record every departure from the strict rules below. A7 scores
are derived from retained answers by `make rescore-a7`. The strict rules below
remain in force for the append-only records.

The evaluator returns `opaque_id`, `option_id`, `support`, `evidence`, and
`rationale`. The scorer uses exact option IDs: correct with explicit support = 3;
correct with inferred support = 2; absence option = 1; foil = 0. An explicit
support quote must occur verbatim in the supplied artifact. That check validates
quotation integrity, not the semantic sufficiency of the quote.

`record_response` retains the full packet and response in an exclusively created
JSON record and appends a summary to `m1_ai.csv`. It rejects duplicate records,
reused evaluator sessions, missing provenance, and repeat configuration changes.
Use one writer. A crash between JSON creation and CSV append requires explicit
reconciliation, not automatic recoding or overwriting the retained response.

Record the agent/configuration hash, evaluator identity, available model/version
settings, invocation/session identifier, packet hash, timestamp, and pass number.
Provider settings that are unavailable must be recorded as unknown. The pilot
used the VS Code picker default; the underlying provider model/version and
temperature were not exposed. Local invocation labels are not provider session
IDs. Freeze and record the available study configuration before study evaluation.

## Repeatability

Before first-pass evaluation, save the complete assignment IDs and the
seed-selected 20% repeat sample, rounded up. Never select repeats after reading
responses. Each repeat receives the identical packet in a new context under the
same recorded evaluator configuration.

`repeatability` requires complete first-pass coverage, the seed-selected sample,
complete repeat records, and isolation evidence. Unweighted Cohen's kappa below
0.6 or undefined blocks substantive findings. This is AI repeatability, not
human reliability or validity. Do not recode toward a passing result.

## Pilot Boundary

Pilot probes, packets, answers, and artifacts are disposable and must not be
reused in the study. Only aggregate engineering findings remain in the runlog.
Passing pilot plumbing checks does not take L2, validate the study instrument,
or demonstrate study repeatability.
