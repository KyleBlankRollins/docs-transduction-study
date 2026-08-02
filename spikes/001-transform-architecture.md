# Spike 001 — Transform architecture and build strategy

**Status:** not started
**De-risks:** [ADR-0002](../decisions/0002-surgical-source-patching.md) (surgical patching), [ADR-0003](../decisions/0003-two-full-site-builds.md) (two full builds)
**Timebox:** two days. If it runs long, that is itself the answer — see *Fallbacks*.

Both ADRs are accepted on reasoning, not evidence. Each rests on an assumption
about real Astro MDX that has never been checked, and each would be expensive to
discover wrong after the transform is rewritten. This spike checks the
assumptions before that work starts.

**Spike code is throwaway.** It does not go in `pipeline/`, it is not committed
beyond a scratch branch, and nothing it produces is used as a study artifact.
Findings go in `runlog.md`; the ADRs get their status updated.

## Prerequisite

Real specimens. This needs the corpus pinned and a provisional specimen list —
roughly M1 — but **not** the relation inventory, probes, or any lock. Three or
four pages chosen for component density are enough; they do not have to be the
final selection.

## Part A — Does surgical patching hold up?

ADR-0002 rests on byte offsets being reliable throughout real MDX. Confirmed so
far only for top-level nodes on a synthetic fixture.

| # | Question | Pass looks like |
| - | -------- | --------------- |
| A1 | Do **nested** MDX JSX nodes carry position offsets in real Astro MDX? | Every `<TabItem>`, nested `<Steps>`, and aside inside a container reports `position.start.offset` and `.end.offset` |
| A2 | Do offsets round-trip exactly? | `source.slice(node.start.offset, node.end.offset)` reproduces that node's source text verbatim, for every container node in every specimen |
| A3 | Can untouched children be spliced back byte-identically? | A code block inside a `<Steps>` item survives a patch of its parent with zero byte difference |
| A4 | Does recursive descent converge on real nesting? | No specimen requires more depth than the implementation handles; record the deepest nesting actually found |
| A5 | Does patched output still build? | The de-marked specimen builds through Astro without error |

**A1 and A2 are the load-bearing ones.** If either fails, ADR-0002 fails.

Worth recording regardless of pass/fail: the deepest real nesting found, and
whether `<Tabs>` wrapping `<Steps>` actually occurs in the corpus. That
combination is the paradigm case for DM-1 and for the design's worked example, and
right now its frequency is assumed rather than known.

## Part B — Does the two-build strategy hold up?

| # | Question | Pass looks like |
| - | -------- | --------------- |
| B1 | Does `withastro/docs` build at the pinned SHA? | Clean build; Node version and package manager recorded |
| B2 | Is the build deterministic? | Two builds of the same tree produce identical HTML for the specimen pages |
| B3 | What is the right A3 extraction target? | An element selector that yields specimen prose without sidebar, header, footer, or search chrome |
| B4 | How much chrome survives extraction? | Chrome is a small fraction of extracted text, and does not dominate A4 chunks |
| B5 | What does a build cost? | Wall-clock time per build, recorded — it multiplies through every pilot re-run |

**B1 is a hard gate.** Everything else in Part B is moot if the pinned tree does
not build.

B4 deserves more attention than it looks like it needs. If theme chrome dominates
the chunks at A4, then chunking is partly measuring the Starlight theme rather
than the page, and that would affect every H1 and H3 number at that stage.

## Fallbacks

Decided now, so a failing spike does not turn into an improvised decision.

| If | Then |
| -- | ---- |
| A1 or A2 fails | ADR-0002 fails. Fall back to normalizing both arms — the option D-8 recommended. That reopens D-8, requires a design edit to *The marking manipulation*, and so **gates L1**. Mark ADR-0002 Rejected and write the replacement record. |
| A3 fails but A1/A2 pass | Patching works but child preservation does not. Narrow ADR-0002 to leaf-level rules (D4, and D3 where the body is a single paragraph) and normalize for the rest. Hybrid, and it needs its own record. |
| A5 fails | Diagnose before concluding. Likely a splicing bug rather than an architectural problem. |
| B1 fails | Fall back to the minimal harness from D-3, and **state the O1/O2 limitation in publication** — deixis and reference would then be measured against fabricated page context, which weakens H2 specifically. |
| B2 fails | Generate artifacts once and archive them; never regenerate. Record as a deviation. |
| B4 fails | Reconsider the extraction target, or the chunker parameters, or both. Do not proceed to L2 with chunks that are mostly theme. |

## Exit

The spike is done when every question above has a recorded answer in `runlog.md`,
each ADR's status is updated to reflect what was learned, and any fallback taken
has its own decision record. A spike that ends without changing or confirming
either ADR's status has not ended.
