/**
 * The de-marking driver: explicit-arm MDX in, implicit-arm MDX plus a report out.
 */

import { parseMdx, stringifyMdx } from "./mdx.js";
import { RULES } from "./rules/index.js";
import type { RuleContext } from "./rules/rule.js";
import type { Templates } from "./templates.js";
import { ALL_RULES, type DemarkReport, type DemarkResult, type RuleSet } from "./types.js";

export interface DemarkOptions {
  templates: Templates;
  /** Path recorded in the report. Not read from disk. */
  file?: string;
  /** Subset of rules to run. Defaults to all; any subset is a run-log deviation. */
  rules?: RuleSet;
}

export function demark(source: string, options: DemarkOptions): DemarkResult {
  const { templates, file = "<inline>", rules = ALL_RULES } = options;

  const tree = parseMdx(source);
  const ctx: RuleContext = { templates, hits: [], exceptions: [] };

  for (const rule of RULES) {
    if (!rules.has(rule.id)) continue;
    rule.apply(tree, ctx);
  }

  const report: DemarkReport = {
    file,
    templateVersion: templates.version,
    templatesFrozen: templates.frozen,
    hits: ctx.hits,
    exceptions: ctx.exceptions,
  };

  return { mdx: stringifyMdx(tree), report };
}

/** Counts of hits by rule, for the run log and the per-specimen sign-off. */
export function summarize(report: DemarkReport): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const hit of report.hits) {
    counts[hit.rule] = (counts[hit.rule] ?? 0) + 1;
  }
  return counts;
}
