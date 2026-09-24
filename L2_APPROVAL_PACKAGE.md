# L2 Approval Package (prepared 2026-09-23; nothing locked, committed, or run)

Three approvals are requested, in this order. Each is separate; none is implied
by another.

## 1. Bounded live smoke test (provider quota)

- Command: `uv run python -m docs_transduction_study.opencode_runner smoke --output /tmp/m1ai-smoke`
- Content: three disposable synthetic packets (no study material) plus one
  repeat, with provider/model `opencode-go/glm-5.3-flash`, temperature 0.
- Bound: at most **6 CLI invocations**, including at most one transport retry per
  packet. On the loopback check each invocation made exactly one provider request
  (the title call is suppressed). Expected usage is under 10k tokens. The run
  stops on any quota or rate error, with no provider failover.
- Checks: authenticated inference; the live export's provider and model IDs;
  reasoning-part handling; answer-JSON compliance; one step per session; no tools;
  fresh session IDs; and the repeat path.
- Prerequisite (maintainer action): confirm OpenCode Go's account-level
  **"Use balance" fallback to Zen credits is OFF**. The CLI cannot show it. Also
  confirm that Go's "typical coding agent traffic" terms cover this workload.
- Afterwards: record the aggregate results in the runlog, dispose of the smoke
  outputs, then freeze `coding/AI_PROTOCOL.md` (configuration sha256 from
  `configuration_record`, CLI 1.18.32).

## 2. L2 lock (after step 1 and the protocol freeze)

Current lock-set hashes (sha256):

| File                            | sha256                                                                                                                          |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| corpus/specimens.csv            | 04a50e5e1008a53278a1eb01506eca300aa4fa0ede70bd6b0dd75874cb9d05c4                                                                |
| instruments/instances.csv       | f92c8d6c8ad64a8cae1c7e8ba419a02a8106aa1fdecb1995610fd6121117da44                                                                |
| instruments/probes.csv          | 0faebb9b548693882cfac63f5c5f849650bfaeb410632a8964a85273985d705a                                                                |
| instruments/gate_exclusions.csv | 012089d1e87213d155565d3f80ce2a667834c36fd0c7a8c442d96536479b0f42                                                                |
| pipeline/demark/templates.json  | c4c7941d21a3b66f09e2cdef2560525f8f54fddf7a06df9e5aaf52e1477d5967                                                                |
| coding/seed                     | 8c8031de5c5b903aee37ef97782875dfa86642a8df9cb31c28d8098ba1e96a7d (value sha256[:16] `107b0d1a5e139067`, as recorded 2026-09-08) |

The study driver also checks that `src/docs_transduction_study/locators.py` (the
normalization spec) and `coding_ai.py` (the prompt and scoring) match the lock
commit.

Instrument: 242 instances. There are 13 dated exclusions: one single-step Steps
block, plus 12 legacy R3 rows that matched `<aside>` inside code examples.
Probes: 229 (R1 31, R2 34, R3-D3 49, R3-D4 0, R4 9, O1 54, O2 52), including
3 version-change probes with verified pre-change SHAs. The R4 shortfall (9 < 20)
is disclosed. The gate was answered by the authoring assistant from both A0
arms, with verbatim evidence (`instruments/gate_evidence.csv`); it is **not
independent**. The linter is structural only.

Decisions needed:

1. **Seed:** commit the raw `coding/seed` in L2 (recommended: M1-AI blindness
   relies on isolated sessions, not on hiding the seed, and the author holds the
   mapping anyway), or commit only its checksum and keep the seed out of band.

   answer: commit the raw seed

2. **Commit scope:** the working tree holds substantial uncommitted work (earlier
   takeover changes plus this readiness work). Because the driver verifies
   `locators.py` and `coding_ai.py` against the lock commit, the proposal is:
   - (a) a readiness commit of the code, tests, docs, and authoring provenance
     (`instruments/authoring/`, `occurrence_decisions.csv`, `gate_evidence.csv`,
     `coding/AI_PROTOCOL.md`, the M2 files);
   - (b) the **L2 commit**, naming the six files explicitly, not blanket staging;
   - (c) a follow-up commit writing `instrument_locked` and
     `instrument_lock_commit` into DESIGN.md frontmatter, plus a runlog L2 entry.

   Verify with `git cat-file -t <sha>`, `git show --name-only <sha>`, and
   `make anchors` (runs `verify-lock`).

   answer: sounds good. I was planning to ask you to break the work into a set of commits anyway.

## 3. Full study run (after L2)

1. `make artifacts PASSPHRASE_FILE=/outside/repo/pass` builds A1–A4 once,
   archives them, resolves anchors, and seals keys. It records `max_packet_bytes`
   and per-stage sizes. Any anchor failure stops the run and requires a
   mechanical amendment.
2. Volume: **1,832 first-pass + 367 repeat = 2,199 invocations minimum**
   (N = 229), before retries (at most 1 per assignment, transport failures only).
   Order sha256 `63da66ab…d5d12`.
3. Context and cost: A1 is a complete compiled page and A2 a complete snapshot;
   both include site navigation. Their sizes are unknown until artifacts exist
   (none may be generated before L2). The model limit is a 1M-token context and
   packets over 1.5 MB are refused, never truncated. A rough bound, assuming
   A1 ≈ 100–170k tokens and A2 ≈ 20–50k per packet, is ~60–110M input tokens.
   At catalog rates ($0.15/M input) that is roughly $10–20 of Go quota, plus
   unknown reasoning tokens. That likely spans several of Go's 5-hour windows
   (20% of the monthly limit each). **Set `MAX_INVOCATIONS` after step 1
   measures the real sizes.** Present that budget for approval before any run.
4. Commands: `make m1-ai-first-pass MAX_INVOCATIONS=… PASSPHRASE_FILE=…`, then
   `make m1-ai-repeat …`, then `make kappa` and `make analyze`. Runs are
   resumable: recorded assignments are skipped; invalid or isolation-failed
   answers are final (never rerun); quota or rate errors stop the batch; there is
   one writer lock; `opencode_runner reconcile --output coding` repairs a CSV
   after a crash, from retained JSON only.
5. Kappa below 0.6, undefined kappa, incomplete coverage, or missing isolation
   evidence withholds substantive tables. The failure report is then the
   publishable result.

Out of scope, not authorized: A5, closed-book covariates, M1b, expanded Phase 2,
and publication.
