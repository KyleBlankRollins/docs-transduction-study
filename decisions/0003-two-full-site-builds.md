# ADR-0003 — Produce A1 from two full builds of the pinned docs site

- **Status:** Accepted with build-determinism deviation (spike 001 passed B1; rotating promotional content prevents strict B2 determinism, so one build must be archived). **Deviation dispositioned by [ADR-0005](0005-deterministic-ad-overlay.md):** the ad-pinning overlay restores determinism; B2 is re-scored at the P5 pilot with the overlay applied. Archive-once remains the operating rule.
- **Supersedes:** the minimal-harness decision recorded as D-3 in `IMPLEMENTATION_PLAN.md`
- **Date:** 2026-08-02
- **Relates to:** `DESIGN.md` → _Pipeline_ (A1); H2

## Context

D-3 chose a minimal Starlight harness for A1: a fresh Starlight project with
specimens dropped in, both arms as sibling pages. Cheap, pinnable, reproducible,
with a fidelity check against the real site deferred to the M4 pilot.

Reconsidering the transform architecture surfaced what that decision
under-weighted: **the observed relations depend on page context the harness does
not have.**

O1 (reference) and O2 (deixis) are naturally occurring and never manipulated, and
H2 predicts deixis is the most fragile type. But "as described above," "see
below," and "the previous step" resolve — or fail to — against the surrounding
page: sidebar, breadcrumbs, previous/next links, real cross-page hrefs, real
heading structure. A minimal harness fabricates all of that.

Fabricating the context in which deixis resolves, in a study whose second
hypothesis is about deixis fragility, is not a fidelity risk to be checked later.
It is measuring the harness.

## Decision

A1 comes from **two complete builds of the same pinned docs tree**, differing only
in the content of the specimen files.

- One submodule pinned at the corpus SHA is the explicit tree.
- A committed script materializes the implicit tree into a gitignored working
  directory: copy the pinned tree, overwrite specimen files with their de-marked
  variants, build.
- Both builds have **identical page sets, routes, sidebars, and navigation.** The
  only difference anywhere in either site is specimen file content.
- The de-marked specimen files are committed on their own, separately from the
  build, as the reviewable diff.
- A3 extracts from the page's article element, not the whole document. Recorded
  as a configured choice, applied identically to both arms.

Two clones are not committed. One submodule plus a generation script gives the
same result reproducibly, without duplicating a large third-party repository in
this repo's history.

## Consequences

**Deixis and reference are measured in the context they actually occur in.** This
is the whole reason for the change, and it is what makes H2 a claim about
documentation rather than about a test rig.

**Nav perturbation disappears.** The variant-pages-in-one-site option considered
under D-3 changed sidebar generation by adding pages; two builds of the same page
set cannot. Route parity between arms is guaranteed rather than arranged.

**A2 gets a realistic accessibility tree** — real landmarks, real nav regions —
which matters because A2 is where component-level marking like Starlight's tab
`tablist` roles plausibly survives before A3 destroys it. That is the sharpest
single prediction in the design, and it deserves to be tested against real markup.

**The costs are operational and real:**

- Two full Astro builds of a large third-party site per pipeline run. Slower, and
  it puts a working build of someone else's repository at a pinned SHA on the
  critical path.
- A pinned SHA may not build with a current toolchain, and the older the pin the
  worse that gets.
- Full-page extraction pulls in sidebar, header, footer, and search chrome. The
  article-element extraction target above is a mitigation, but choosing an
  extraction target is now a configured decision that shapes every A3 and A4
  artifact.
- Build determinism is assumed, not established. Two runs of the same tree should
  produce the same HTML; if they do not, artifacts must be generated once and
  archived rather than regenerated.

### What to watch

- **Whether the pinned SHA builds at all**, and with which Node and package
  manager. If it does not, either move the pin or fall back to the harness.
- **How much chrome survives article-element extraction**, and whether it swamps
  specimen content in the A4 chunks. If chrome dominates the chunks, chunking is
  measuring the theme rather than the page.
- **Build determinism across runs.** Check before generating scored artifacts.
- **Build time**, only because it multiplies through every re-run during the pilot.

## Alternatives rejected

- **Minimal Starlight harness** (the D-3 decision). Cheap and reproducible, but
  fabricates exactly the page context H2 measures. The fidelity check D-3 deferred
  to M4 would have compared A3 text, which would not have caught a missing sidebar
  or absent prev/next links — the check was aimed at the wrong difference.
- **One site with implicit variants added as extra pages.** Perturbs sidebar and
  nav generation, so the arms differ in site structure as well as marking.
- **Real site for the explicit arm, harness for the implicit arm.** Introduces a
  rendering difference between arms. Rejected under D-3 and still rejected.
- **Two committed clones.** Same builds, but duplicates a large repository in this
  repo's history for no gain over a submodule plus a generation script.

## Effect on registration

**Does not gate L1.** The design's A1 row already says "Starlight build output,"
which two builds satisfy; no design wording changes.

**Gates artifact generation (M6)** and should be validated at the M4 pilot, which
is before L2. The extraction target and the build toolchain versions are recorded
in `runlog.md` as configured choices, in the same way the chunker parameters
already are.
