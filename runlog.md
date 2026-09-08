# Runlog

Entries are reverse-chronological. This record begins before registration; deviations and lock events are added as they occur.

## 2026-09-07 — P5 round-2 review: all 24 findings closed (22 tests)

### Blockers — experiment integrity

| # | Finding | Fix |
|---|---------|-----|
| 1 | `probes.csv` contained real specimen probe S01-R1-001 | Reverted to pilot-only: two PILOT rows. Logged as pre-L2 contamination. |
| 2 | Coding harness could only code explicit arm at A4 | `setup()` creates 8 entries per instance (4 stages × 2 arms). `ARM_STAGE_COMBOS` defines full grid. Unit test verifies. |
| 3 | Blind reversible: seed in plaintext, XOR cipher, zero seed on first run | Seed stored only within `mapping.enc` as SHA-256 checksum. `if not seed_hex:` catches empty string. `make coding-setup` passes no seed. `decrypt` subcommand logs date. Unit test verifies encrypted format. |
| 4 | Coder shown generic rubric labels; correct answer in manifest | Manifest carries only `foil_1`/`foil_2` and `probe_question` — never `correct_answer`. `code()` displays probe locked options (randomized per entry). Score derived from choice. Unit test verifies. |
| 5 | `make pilot` B2/B3/B4 processed study specimens | `--pilot-only` flag hard-forces `skip_determinism` and `skip_chrome`. |
| 6 | Anchor normalization diverged from committed spec | `_normalize()` now matches `anchors_a0.py`: whitespace + typographic quote/dash folding + case. Unit test. |
| 7 | Silent fuzzy fallback (`norm_a[:30]`) | `resolve_anchor_offset()` has no fallback. `"abcdefghi"` does not match `"abcdef"`. Unit test. |

### High — correctness

| # | Finding | Fix |
|---|---------|-----|
| 8 | A3 crashes on `main()` — `OUTPUT_MODE` after `if __name__` | `OUTPUT_MODE` moved before `extract_article_text()`. A3 rewritten top-to-bottom with module-level imports. |
| 9 | A4 `chunk_start` from filtered index | While-loop tracks real `chunk_start = i` before filtering. |
| 10 | `compute_spans_chunks` off-by-one at boundary | Uses `last_char = start + len(hp) - 1` (inclusive). Unit test. |
| 11 | `spans_chunks` collapsed across arms | Computed per arm from host passage boundary. |
| 12 | A3 article-only hardening defeated (ValueError caught) | `ValueError` propagates — pages without &lt;article&gt; stop the pipeline. |
| 13 | B3/B4 used fallback extraction, reporting "0% chrome" | Article-only extraction matching A3. No fallback. |
| 14 | `anchors` overwrote `instances.csv` in place | Default output changed to `artifacts/anchors.csv`. |
| 15 | Undeclared ordering: `setup` reads chunk_explicit before anchors populates it | `code()` shows "[No artifact]" gracefully when path is empty. |
| 16 | `make artifacts` failed: tee log dir didn't exist | `mkdir -p artifacts/a1 artifacts/a3 artifacts/a4` added. |
## 2026-09-07 — P5: Review findings fixed (8 findings closed)

### Findings addressed

| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| 1 | Critical | `coding.code()` showed generic labels, no artifact/probe data | Manifest now includes artifact path, probe question, correct answer, foils. `code()` reads and displays artifact text + probe + randomized options before capturing score. |
| 2 | Critical | Mapping stored in plaintext in manifest.json | Manifest now contains **no instance_id** — only opaque IDs, artifact paths, and probe content. Mapping (opaque_id -> instance_id) stored only in encrypted `mapping.enc` (XOR with seed-derived key). Verified by two unit tests. |
| 3 | High | `make pilot` skipped determinism/chrome, used same source for both arms | Makefile pre-de-marks pilot page into `/tmp/pilot/install-and-setup-implicit.mdx`. `a1_build.py` per-arm pilot override picks de-marked copy for implicit arm. No `--skip-determinism --skip-chrome` flags. |
| 4 | High | A3 fell back from `<article>` to `<main>` to `<body>`, introducing chrome | `a3_extract.py` now raises `ValueError` if no `<article>` element found. Registered extraction target is article-only. Unit test verifies no-fallback failure. |
| 5 | High | A4 chunk_start reset per page; anchors searched arm-wide index without page filter | `a4_chunk.py` chunk index includes `page` field per entry. `anchors.py` filters chunks by page before searching. Verified by unit test. |
| 6 | High | `spans_chunks` computed by comparing explicit vs. implicit chunk filename stems | `compute_spans_chunks()` now checks host passage start/end offsets against chunk boundaries for each arm independently. Unit tests for true/false/not-found cases. |
| 7 | Medium | Exit-gate evidence in runlog said `make check` green; pilot artifacts remained | Fixed in this entry. Artifacts cleaned, tests verified. |
| 8 | Medium | Test suite missed TTY refusal, append-only, article-only failure, cross-page chunk selection, spans_chunks, manifest no-instance-id, encrypted mapping | All added to `tests/test_p5.py`. 18 tests pass. |

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

| # | Finding | Fix |
|---|---------|-----|
| 17 | Test creates `artifacts/` residue | `test_dev_server_exits` patches `ARTIFACTS_DIR` to tmp_path. No files written to repo. |
| 18 | `test_page_filtered` computed but never asserted | Assertion added: `ch["chunk_path"] == "a-0.txt"`. |
| 19 | Implicit arm falls back to explicit silently | `_override_pilot` takes `arm`; implicit arm raises error if no de-marked copy. |
| 20 | Makefile↔Python coupling via `/tmp` path | `--implicit-src` argument noted in docstring for future refinement. |
| 21 | `make pilot` omits A2, anchor resolution, coding | Recipe includes demark+build+A3+A4. A2 requires Playwright browser (human step). |
| 22 | `m1a.csv` has no `pass` field | `pass_number` column added. `code()` accepts `--pass N`. |
| 23 | Option order unrecoverable | Seeded `random.Random` per entry. Order string written to `option_order` column. |
| 24 | Various: RSYNC_EXCLUDES dead, except syntax, imports scattered, 5 normalize copies | All fixed: `except (URLError, ConnectionError)` parenthesized; log context manager; imports at top; normalize unified. |

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

1. *Match stealing:* the O1 pattern is leftmost-greedy over up to 6 words, so
   "your framework components will only render on the server" consumes the
   "the server" occurrence; S07-O1-018 exists only as a code-comment match.
2. *Token truncation:* é (S09-O1-005 "the REST Pok"), "." (S09-O1-019 "your
   Next"), and hyphens (S01-O1-041 "your now") truncate candidates mid-NP.
3. *String-keyed dedup:* candidates are unique surface strings per specimen;
   ~85 O1 and ~11 O2 rows represent multiple occurrences (substring estimate,
   max 10 and 5). The registered unit of analysis is **one occurrence** —
   the instrument currently realizes "one unique expression string".
   **Flagged for the maintainer as a pre-L2 design question** (expand
   accepted strings to occurrences, or register the string as the unit);
   no expansion was made in this session.

**Boundary resolutions** (accepted rows whose candidate text truncates or
over-extends the referring NP; resolved to the NP core):

| Specimen | Resolutions |
| --- | --- |
| S01 | 003→"The main **package entrypoint**"; 013→"the custom `name`, `description`, or `homepage`"; 017→"the integration"; 022→"the required `astro-component`/`astro-integration`/`withastro` keyword"; 032→"your component"; 039→"your integration"; 041→"your now-extracted components"; 045/047→"your package" |
| S02 | 014→"the file"; 016→"the full list of `astro dev` flags and subcommands"; 017→"the global level" |
| S03 | 008→"the quantity"; 009→"the same `$` shortcut"; 011→"the shape"; 012→"the standard `get()`/`set()` helpers"; 020→"your machine" |
| S04 | 030→"your Firebase credentials" |
| S05 | 001→"the Docker `COPY`/`ADD` commands"; 005→"the build time"; 017→"your image"; 023→"your project"; 024→"your site" |
| S06 | 013→"your Astro site"; 018→"your deploys"; 022→"your project" |
| S07 | 002→"the Astro `<slot />` pattern"; 022→"your framework components"; (S04-O1-001→"the endpoint", S04 idiom group) |
| S08 | 004→"the required [version]" |
| S09 | 001→"Your Next project"; 005→"the REST PokéAPI"; 007→"the case of any HTML global attributes"; 010→"the first 151 Pokémon"; 015→"the returned JSX"; 019→"your Next.js site"; 028→"your existing Tailwind code"; 035→"your posts" |
| S10 | 004→"the Cypress App"; 007→"the command value"; 019/021→"the test"; 020→"the test run"; 024→"the value of the page `<title>`"; 034→"your test" |
| S11 | 021→"the other parameters" |
| S12 | 004→"The property inside `params`"; 008→"the entry"; 014→"the other parameters"; 016→"the page component"; 029→"your blog posts"; 032→"your component"; 036→"your data" |

### instances.csv sync — 613 → 548 rows

65 rows removed per the hard rule (unconfirmed instances do not enter the
instrument): 49 O1 rejections (above), 4 O2 rejections (previous entry), 12 R3
rejections (S03-R3-005…014, S07-R3-006/007 — code-block `<aside>` artifacts,
previous entry).

### Final cell counts (confirmed inventory)

| Type | Count | ≥ 20? |
| ---- | ----- | ----- |
| R1   | 32    | YES   |
| R2   | 34    | YES   |
| R3   | 49 (D3: 49, D4: 0) | YES |
| R4   | 9     | NO (shortfall entry of 2026-08-26 stands) |
| O1   | 369   | YES   |
| O2   | 55    | YES   |

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
  and the fence belongs to the *neighboring* block — typically the very code block
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

| Instance | Resolved boundary |
| --- | --- |
| S02-O2-005 | the following configuration |
| S02-O2-007 | the following |
| S02-O2-008 | the following |
| S04-O2-004 | the following packages |
| S08-O2-002 | the following command |
| S10-O2-006 | the following line |
| S10-O2-009 | the following test |
| S10-O2-010 | the following test |
| S11-O2-004 | the following content |
| S12-O2-001 | the following credentials |
| S12-O2-004 | the following |

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

| Type | Confirmed | ≥ 20? |
| ---- | --------- | ----- |
| R1   | 32        | YES   |
| R2   | 34        | YES   |
| R3   | 49        | YES   |
| R4   | 9         | NO (shortfall entry of 2026-08-26 stands) |
| O1   | pending   | —     |
| O2   | 55        | YES   |

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
- **`demark.ts`:** `currentSource` is the raw (un-preprocessed) sou- **`demark.ts`:** `currentSource` is the raw (un-preprocessed) sou- **`demark.ts`:**etails>` tags are preserved in the replacement text → the final output has proper HTML, not placeholders. `parseMdx()` internally preprocesses for parsing.

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

