/**
 * The de-marking driver: explicit-arm MDX in, implicit-arm MDX plus a report out.
 *
 * Per ADR-0002, the transform patches source ranges by byte offset rather than
 * re-serializing the document. Patches are applied by fixpoint iteration:
 * each pass applies all container rules to top-level nodes, then re-parses
 * to pick up containers that were nested inside previously patched ones.
 * D4 (keyword lowercasing) runs on the final pass only.
 *
 * Known parser edge case: HTML elements like `<details>` inside container
 * directives (:::) are pre-processed to avoid MDX JSX parser failures.
 * The replacements are same-length space-padded markers, preserving byte
 * positions for source patching.
 */

import { parseMdx } from "./mdx.js";
import { RULES } from "./rules/index.js";
import type { RuleContext } from "./rules/rule.js";
import type { Templates } from "./templates.js";
import {
  ALL_RULES,
  type DemarkReport,
  type DemarkResult,
  type Patch,
  type RuleId,
  type RuleSet,
} from "./types.js";

export interface DemarkOptions {
  templates: Templates;
  /** Path recorded in the report. Not read from disk. */
  file?: string;
  /** Subset of rules to run. Defaults to all; any subset is a run-log deviation. */
  rules?: RuleSet;
}

/** Maximum fixpoint iterations to prevent infinite loops. */
const MAX_PASSES = 10;

/**
 * Apply a set of patches [start, end) → replacement to `source`.
 * Patches must be sorted ascending by start offset and must not overlap.
 * Applied right-to-left so earlier byte offsets remain valid.
 */
export function applyPatches(source: string, patches: Patch[]): string {
  if (patches.length === 0) return source;

  // Sort by start offset descending so rightmost patches apply first
  const sorted = [...patches].sort((a, b) => b.start - a.start);

  // Validate non-overlap
  for (let i = 0; i < sorted.length - 1; i++) {
    const c = sorted[i]!;
    const n = sorted[i + 1]!;
    if (n.end > c.start) {
      throw new Error(
        `Overlapping patches: [${n.start},${n.end}) and [${c.start},${c.end}) overlap`,
      );
    }
  }

  let result = source;
  for (const patch of sorted) {
    result =
      result.slice(0, patch.start) +
      patch.replacement +
      result.slice(patch.end);
  }
  return result;
}

/**
 * Container rules (D1, D2, D3, D7, D8) that run in the fixpoint loop.
 * D4 (text-level keyword substitution) runs once on the final pass.
 */
const CONTAINER_RULE_IDS: ReadonlySet<RuleId> = new Set(["D1", "D2", "D3", "D7", "D8"]);

export function demark(source: string, options: DemarkOptions): DemarkResult {
  const { templates, file = "<inline>", rules = ALL_RULES } = options;
  const ctx: RuleContext = { templates, hits: [], exceptions: [] };

  // Build active rule lists
  const containerRules = RULES.filter((r) => rules.has(r.id) && CONTAINER_RULE_IDS.has(r.id as RuleId));
  const d4Rule = rules.has("D4") ? RULES.find((r) => r.id === "D4") ?? null : null;

  // Keep the original source for patching. preprocessSource() is called inside
  // parseMdx() so the parser sees sanitized input, but patching operates on the
  // real source so placeholder artifacts never leak into output.
  let currentSource = source;
  let passNumber = 0;

  // Fixpoint: repeatedly apply container rules until no more nodes match
  while (passNumber < MAX_PASSES) {
    const tree = parseMdx(currentSource);
    const passPatches: Patch[] = [];

    for (const rule of containerRules) {
      rule.apply(currentSource, tree, ctx, passPatches);
    }

    if (passPatches.length === 0) break;

    currentSource = applyPatches(currentSource, passPatches);
    passNumber++;
  }

  // D4 runs once on the final source — apply its patches to the source
  if (d4Rule) {
    const tree = parseMdx(currentSource);
    const d4Patches: Patch[] = [];
    d4Rule.apply(currentSource, tree, ctx, d4Patches);
    if (d4Patches.length > 0) {
      currentSource = applyPatches(currentSource, d4Patches);
    }
  }

  // If we hit MAX_PASSES, something is wrong
  if (passNumber >= MAX_PASSES) {
    ctx.exceptions.push({
      rule: "D1" as RuleId,
      reason: `Fixpoint did not converge after ${MAX_PASSES} passes — possible infinite loop`,
      line: undefined,
    });
  }

  const report: DemarkReport = {
    file,
    templateVersion: templates.version,
    templatesFrozen: templates.frozen,
    hits: ctx.hits,
    exceptions: ctx.exceptions,
  };

  return { mdx: currentSource, report };
}

/** Counts of hits by rule, for the run log and the per-specimen sign-off. */
export function summarize(report: DemarkReport): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const hit of report.hits) {
    counts[hit.rule] = (counts[hit.rule] ?? 0) + 1;
  }
  return counts;
}
