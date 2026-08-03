# ADR-0005 — Pin the rotating sidebar ad with a build overlay

**Status:** accepted, 2026-08-02. Pre-L1.

## Context

Spike 001's B2 check found that two clean builds of the pinned `withastro/docs` tree differ in 5,112 of 6,313 HTML files. The sole build-output source is `src/components/RightSidebar/RandomizedAd.astro`: it selects one of three promotional ads with `Math.random()` in component frontmatter, which executes at build time, per page, per build. The component is rendered on essentially every content page via the `Footer.astro` and `PageSidebar.astro` Starlight overrides.

The archived-single-build fallback in the spike brief handles reproducibility over time. It does not handle this study's specific exposure: ADR-0003 builds the explicit and implicit arms as **two separate builds**, so per-build randomness injects between-arm differences unrelated to the manipulation — visible in whole-page A2 accessibility trees even where A3's article-scoped extraction excludes it. "Nothing else differs between the arms" is the design's central construction; ad roulette breaks it for free.

Two further `Math.random()` uses (`TabbedContent` tab IDs, `MultipleChoice` keys) run client-side only. They cannot affect build output; whether the tab IDs surface in A2 snapshots is a pilot verification item, not a build concern.

## Decision

A committed overlay at `pipeline/overlays/`, mirroring the corpus tree structure, replaces `RandomizedAd.astro` with a version that statically renders **ScrimbaAd** — one of the two modal-weight (0.4) ads; the specific pick is arbitrary and fixed. The A1 build stage copies the vendor tree into the build workspace, applies the overlay, then (for the implicit arm) applies the de-marking patches, then builds. **The overlay is applied identically to both arms, before either build.** The pinned submodule is never modified.

Verification: the spike's B2 two-build comparison is re-scored at the P5 pilot with the overlay applied, expecting zero differing files; the deferred B3/B4 checks are scored at the same time. Residual nondeterminism, if any, is recorded there.

## Consequences

- A1's "deterministic" label in the design is claimed only with the overlay applied — the design says so as of v0.6.
- Every artifact page carries the same ad, which slightly departs from the live site's rotation. The composition (an ad aside is present) remains realistic; only the variance is removed.
- The overlay is part of the committed pipeline, so a reproducer gets deterministic builds without hidden steps.

## Rejected

- **Remove the ad entirely.** Also deterministic, but changes page composition relative to the site the corpus was written for; freezing preserves composition and removes only variance. Removal remains the fallback if the pinned ad component itself proves unstable.
- **Accept and archive one build per arm.** Leaves the arms differing in promo content on nearly every page; the between-arm confound the two-build design exists to exclude would be reintroduced by chrome.
- **Seed the RNG.** Astro exposes no build-time seed hook; patching `Math.random` globally is far more invasive than replacing one component.
