# Known issues — demark

Open defects in the de-marking transform. Each must be closed, or explicitly
accepted and logged in `runlog.md`, **before L2** — the instrument lock is the
point after which a transform change costs an amendment.

---

## DM-1 — Nested containers are not de-marked (open, blocking)

**Severity: blocking.** Produces a silently wrong implicit arm.

> **Do not fix this in isolation.** [ADR-0002](../../decisions/0002-surgical-source-patching.md)
> rebuilds the transform to patch source ranges instead of re-serializing the
> document, which requires recursive descent and therefore closes DM-1 as a side
> effect. The nesting bug and the formatting confound behind D-8 are the same
> architectural problem. The fix described below is correct for the current
> architecture and is kept as the fallback if [spike 001](../../spikes/001-transform-architecture.md)
> rejects ADR-0002.

### What happens

Every rule iterates `tree.children` — the top level of the document only. Nested
containers are reached only as a side effect: a container rule splices its
children up into the root, where a *later* rule can then see them.

That makes correctness depend on rule order. `RULES` is `[D1, D2, D3, D7, D4]`,
so a nested container is transformed if and only if the outer container's rule
runs **before** the inner one's:

| Outer | Inner | Result |
| ----- | ----- | ------ |
| `<Steps>` | `<Tabs>` / aside / table | de-marked |
| `<Tabs>` | aside / table | de-marked |
| aside | table | de-marked |
| `<Tabs>` | `<Steps>` | **survives untransformed** |
| aside | `<Steps>` | **survives untransformed** |
| aside | `<Tabs>` | **survives untransformed** |
| any container | itself (`<Steps>` in `<Steps>`, …) | **survives untransformed** |

The last row is structural: a rule's backward loop splices at index `i` and
continues at `i - 1`, so nodes it just inserted are never revisited.

All four failing cases are confirmed by hand against the current build.

### Why it matters more than a normal bug

It does not throw. It emits valid MDX that builds through Starlight — and still
contains live Starlight components. The "implicit" variant is then **still
explicitly marked**, at exactly the sites the manipulation was supposed to strip.

Two consequences, in order of importance:

1. **The manipulation silently fails at the sites most likely to matter.** Astro's
   install pages are the paradigm case for `<Tabs>` wrapping `<Steps>` — per
   package manager, each with ordered steps. That is the same construction the
   design uses as its worked example of a corrupted membership relation. The
   pages most central to the study are the pages most likely to be affected.
2. **It biases toward the null.** An implicit variant that keeps its markup looks
   more like the explicit arm, so the measured gap narrows and H1 is
   under-detected. That direction is conservative, which is *not* a reason to
   accept it: the manipulation would not be what the design says it is, and
   discovering that after coding would invalidate the run.

Propositional equivalence is not violated — nothing is dropped. What breaks is the
manipulation itself.

### Why the equivalence review would not catch it

M2's review reads diff hunks against the constraint that no information was lost.
Leftover markup loses nothing, so a reviewer checking for omissions can pass a
file that still contains `<Steps>`. The review is aimed at the wrong failure
direction to catch this one.

### Fix

Two changes, both wanted:

1. **Iterate the rule set to a fixpoint.** Re-run `D1`–`D3`, `D7` until a pass
   records no hits. Terminates because each pass strictly reduces the number of
   container nodes. This is a few lines in `demark.ts` and needs no change to any
   rule. Run `D4` once, on the final pass only — it is idempotent (a lowercased
   keyword no longer matches) but re-running it would double-count hits in the
   report.
2. **Add a post-transform assertion.** After the last pass, fail if the output
   still contains a known Starlight component name or a container directive.
   A guard, not a fix — but it is what turns any future silent failure, including
   from a component nobody enumerated, into a loud one.

Recursive descent inside each rule is the alternative to (1). It is more code and
more surface area for a rule to mishandle an unexpected parent, for no benefit
the fixpoint does not already give.

### Regression tests to add with the fix

- Each failing pair in the table above, asserting no component or directive
  syntax survives in the output.
- Same-rule nesting for `<Steps>`, `<Tabs>`, and asides.
- Three-deep nesting (`<Tabs>` → `<Steps>` → aside), to confirm the fixpoint
  converges rather than terminating after one extra pass.
- Hit counts under the fixpoint, to confirm no double-counting.

---

## DM-2 — Not validated against real Astro MDX (open)

**Severity: unknown until M1 lands.** Every fixture in `test/` is synthetic and
written alongside the code, so the suite demonstrates that the rules do what their
author intended — not that the author's model of Starlight MDX is right.

Specifically unverified:

- Whether Astro's docs use the directive form (`:::caution`), the component form
  (`<Aside type="caution">`), or both, and in what proportion.
- Whether `<Steps>` always wraps exactly one ordered list. The D1 exception path
  assumes it usually does.
- Whether `<TabItem label>` is ever an expression rather than a literal, which D2
  currently refuses to transform.
- Which other Starlight components appear in the specimens and carry a relation
  that no rule covers.
- Whether serialized output actually builds through Starlight. Nothing has been
  through an Astro build.

Close this at **M1/M4** by running the transform across all selected specimens and
reading the reports before any probe is written.

---

## DM-3 — CLI and build not exercised (open, minor)

`npm run build` has never been run, so `dist/` and the `demark` bin have never
been produced. The CLI's argument handling, file I/O, and `--require-frozen` gate
are untested. Cover with a smoke test that runs both modes over a fixture file.
