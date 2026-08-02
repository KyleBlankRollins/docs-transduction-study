# Runlog

Entries are reverse-chronological. This record begins before registration; deviations and lock events are added as they occur.

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
