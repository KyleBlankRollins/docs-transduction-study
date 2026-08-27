# Known issues — demark

Open defects in the de-marking transform. Each must be closed, or explicitly
accepted and logged in `runlog.md`, **before L2** — the instrument lock is the
point after which a transform change costs an amendment.

---

## DM-1 — Nested containers are not de-marked (RESOLVED)

**RESOLVED by the ADR-0002 rebuild (P3).** The transform now uses surgical
source patching with fixpoint iteration: each pass applies all container rules
to top-level nodes, then re-parses to pick up containers that were nested
inside previously patched ones. Nested containers of any combination are
de-marked across passes. The fixpoint converges because each pass strictly
reduces the number of container nodes.

Regression tests covering nested pairs and three-deep nesting pass in
`make check`.

---

## DM-2 — Not validated against real Astro MDX (open)

**Severity: unknown until M1 lands.** Every fixture in `test/` is synthetic and
written alongside the code, so the suite demonstrates that the rules do what their
author intended — not that the author's model of Starlight MDX is right.

**Status update (P3):** The transform has been exercised on all 12 real specimens
(see `corpus/specimens.csv`). Across the corpus, D1 found `<Steps>` in S01, S02,
S05, S06, S08, S09, S10, S11, S12 — all wrapping single ordered lists, no
exceptions. D2 found both raw `<Tabs>/<TabItem>` and custom wrappers
(PackageManagerTabs, UIFrameworkTabs, StaticSsrTabs, JavascriptFlavorTabs). D3
found both `:::directive` and `<Aside>` forms. D8 fired on `## Prerequisites`,
`### Requirements`, and `## What You'll Need` headings.

The build check (`make build-check`) has run all 12 specimens through two full
Astro builds — both arms built 6,313 pages cleanly. Serialized output builds
through Starlight.

Remaining unverified at the rule level:

- Whether `<TabItem label>` is ever an expression rather than a literal, which D2
  currently refuses to transform (raises an exception instead). No such specimens
  were found in the corpus; this is a graceful-degradation path, not a gap.
- Which other Starlight components appear in the full corpus (beyond the 12
  specimens) and carry a relation that no rule covers.
- D4 (RFC 2119 keywords) found no uppercase matches across the 12 specimens.
  Whether the broader corpus contains them is unknown until M4.

Close this at **M1/M4** by running the transform across the full corpus (all
~600 pages) and reading the reports.

---

## DM-3 — CLI smoke test not yet automated (open, minor)

The `demark` CLI runs through `tsx` during development. `npm run build` (tsc)
is exercised by `make check`. However, the compiled `dist/cli.js` requires `node`
invocation via the package.json `bin` mapping, which is not yet smoke-tested
in CI. The CLI's argument parsing, file I/O, `--report`, and `--require-frozen`
gate have been exercised manually during P3 but lack an automated regression
test. Cover with a smoke test that runs both `normalize` and `demark` modes over
a fixture file.
