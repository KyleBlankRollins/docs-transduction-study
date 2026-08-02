# ADR-0002 — Transform by patching source ranges, not by re-serializing the document

- **Status:** Accepted (spike 001 passed; implementation and real-output build validation remain required)
- **Date:** 2026-08-02
- **Relates to:** `IMPLEMENTATION_PLAN.md` → D-8 (superseded by this record); `pipeline/demark/KNOWN-ISSUES.md` → DM-1; `DESIGN.md` → *The marking manipulation*

## Context

The transform as built parses MDX to an AST, mutates it, and serializes the whole
document back. That produces the implicit arm. The explicit arm was to stay
verbatim Astro source.

Serialization is not lossless. Measured on Astro-shaped MDX:

- `*` list bullets rewritten to `-`
- table columns re-padded to aligned widths
- the blank line after frontmatter dropped, shifting everything below it

None of that changes rendered HTML, but all of it survives into **A3 plain-text
extraction**, which is a stage the study scores. So the arms would differ in
formatting as well as marking, and the design's load-bearing claim that "nothing
else differs" would be false.

D-8 framed this as a choice between two bad options: leave the confound in place,
or run the explicit arm through the serializer too so the noise is at least
symmetric. The second balances the problem rather than removing it, and costs the
design's plain statement that explicit variants are "Astro's pages as authored."

There is a third option. Every node from remark carries byte offsets into the
source. Confirmed on a realistic fixture — `yaml 0..63`, `mdxJsxFlowElement
205..304`, `table 333..390`, `containerDirective 392..421`, all present. That
makes it possible to change only the ranges the rules touch.

## Decision

The transform **patches the source string by offset**. For each relation site, it
computes replacement text for that node's source range and splices it in. Every
byte outside a patched range is carried through unchanged.

Consequences of that shape, all intended:

- **The explicit arm is verbatim Astro source.** Nothing is done to it at all —
  no normalize pass, no round trip.
- **The implicit arm is byte-identical to the explicit arm except at de-marked
  sites.** The manipulation is the only difference, by construction rather than
  by argument.
- **Rules descend recursively** rather than walking only the document's top level,
  because patching a range requires knowing the ranges nested inside it.
- Untouched children inside a patched block — a code block inside a `<Steps>`
  item — are spliced back from **original source**, not re-serialized.

## Consequences

**D-8 dissolves rather than being decided.** There is no formatting confound to
balance, so no design change is needed: *"Explicit variants are Astro's pages as
authored"* becomes literally true instead of approximately true. The option D-8
recommended would have required editing that sentence.

**DM-1 is absorbed.** The nesting bug and the formatting confound turn out to be
the same architectural problem — top-level-only iteration over a whole-document
serialization. Recursive descent is required by patching anyway, so fixing the
transform fixes both. DM-1 should not be patched separately; it closes when this
lands.

**The equivalence review gets much stronger.** M2's propositional-equivalence
check reads diff hunks, and the diff *is* the evidence that the manipulation was
mechanical. Under whole-document serialization every specimen diff carries
formatting noise the reviewer has to look past, on every file, with attention
that should be going to content. Under patching, the diff contains the
manipulation and nothing else. That is a real gain in the credibility of the
High-rated strawman mitigation, not just a convenience.

**D4 becomes trivially safe.** Under ADR-0001's lowercasing the replacement is the
same byte length as what it replaces, so those patches cannot perturb any
surrounding offset.

**The cost is implementation complexity**, and it is not small. Splicing untouched
children out of a replaced block means each rule must know which of its
descendants it is rewriting and which it is preserving — bookkeeping the current
design gets for free by handing everything to the serializer. Patch ranges must be
applied outermost-last or by descending offset, or earlier patches invalidate
later offsets.

### What to watch

- **Offsets on nested MDX JSX nodes in real Astro MDX.** Verified at the top level
  on a synthetic fixture only. If nested JSX children lack reliable positions, the
  whole approach fails and D-8 reopens. This is the spike's first question.
- **Boundary drift.** Replacement text is still produced by the serializer, so
  whitespace at the seam between patched and unpatched regions is where breakage
  will show up if it shows up.
- **Patched output must still build through Astro.** Valid MDX is not guaranteed
  by valid splicing.

## Alternatives rejected

- **Normalize both arms** (what D-8 recommended). Balances the confound instead of
  removing it, makes `corpus/explicit/` not-verbatim, and requires editing the
  design's description of the explicit arm. Strictly worse if patching works —
  which is why the spike exists. This remains the fallback.
- **Serialize the implicit arm, leave the explicit arm verbatim** (the status quo).
  Carries a known formatting confound into every scored stage. Rejected.
- **Fix DM-1 on its own and revisit later.** Would mean writing recursive descent
  twice, and would leave the confound in place for however long "later" is.
- **Regex over source.** Surgical in the same sense and much cheaper, but gives up
  the parse that makes the manipulation defensible. Already rejected in D-2 and
  not reopened here.

## Effect on registration

**Does not gate L1** — that is the point of it. It requires no design change,
because it makes the design's existing wording true.

**Gates L2.** The transform must be rebuilt and spiked before implicit variants
are generated and the instrument is locked. If the spike fails and the fallback is
taken, D-8 reopens *and* gains a design edit, so it would then gate L1 after all.
