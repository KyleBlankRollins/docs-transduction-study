# Runlog

Entries are reverse-chronological. This record begins before registration; deviations and lock events are added as they occur.

## 2026-08-02 — Amendments A1–A2 taken: D8 added, stale D4 wording repaired; design at v0.7

- **A1 (maintainer-approved):** de-marking rule **D8** added — prerequisite-heading blocks lose their heading; content stays in place, introduced by a template sentence asserting the precondition relation (template frozen at L2 with the rest). Resolves the flag in the previous entry: the manipulated R4 cell can now draw on the corpus's dominant idiom (48 pages). First post-registration amendment; results not seen — no instrument, no artifacts exist.
- **A2:** while drafting A1, the registered text was found internally inconsistent — the templates paragraph still prescribed the 0.3 `MUST` → "needs to" mapping that 0.4 replaced with lowercasing (ADR-0001). Repaired. No study behavior changes.
- Recorded in `AMENDMENTS.md`, in the design's own amendment log (both copies), and propagated: plan W2/§3, phases P3/P4, P0 version gate (0.6→0.7). Status header updated to reflect the registered state.

## 2026-08-02 — R4 column added to the component report

- `prereq_count` added to `corpus_report.py`: `##`/`###` headings containing "Prerequisites"/"Requirements" (the corpus's dominant precondition idiom — 60 headings across 48 pages, no competing styles found) plus prerequisite-titled asides (`:::note[Prerequisites]`). Regenerated: 62 markers across 50 pages. Titled asides also appear in `aside_count`; the columns are selection signals, not a partition.
- **Flag for the maintainer:** heading-marked prerequisite blocks have no de-marking rule in the frozen design (D6 was deliberately cut at v0.3), so R4's *manipulated* cell can draw only from aside-carried preconditions (D3) and tables (D7, ≈3 pages corpus-wide). Decision pending: accept a narrow R4 cell and record the shortfall, or amend (pre-data, labeled) to add a heading-unmarking rule.

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
