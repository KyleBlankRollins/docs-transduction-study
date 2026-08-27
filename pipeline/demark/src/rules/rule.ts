import type { Root } from "mdast";
import type { Templates } from "../templates.js";
import type { Patch, RuleException, RuleHit, RuleId } from "../types.js";

export interface RuleContext {
  templates: Templates;
  hits: RuleHit[];
  exceptions: RuleException[];
}

export interface Rule {
  readonly id: RuleId;
  readonly description: string;
  /**
   * Identify target nodes in the parsed tree and push patches for them.
   *
   * The source string is the current state after previous passes' patches
   * have been applied. Rules walk top-level children only (the fixpoint loop
   * handles nesting: when a parent container is replaced, its children become
   * top-level in the next pass).
   *
   * Child content for replacement text is extracted via source.slice() using
   * node position offsets, preserving verbatim text without re-serialization.
   */
  apply(source: string, tree: Root, ctx: RuleContext, patches: Patch[]): void;
}

export function record(ctx: RuleContext, rule: RuleId, detail: string, line: number | undefined): void {
  ctx.hits.push({ rule, detail, line });
}

export function except(ctx: RuleContext, rule: RuleId, reason: string, line: number | undefined): void {
  ctx.exceptions.push({ rule, reason, line });
}

/**
 * Extract the verbatim source text for a node.
 * Returns undefined if the node has no position offsets.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function nodeSource(source: string, node: any): string | undefined {
  const pos = node?.position;
  if (!pos) return undefined;
  const start = pos.start;
  const end = pos.end;
  if (!start || !end) return undefined;
  const startOffset = start.offset;
  const endOffset = end.offset;
  if (startOffset == null || endOffset == null) return undefined;
  return source.slice(startOffset, endOffset);
}

/**
 * Trim leading/trailing blank lines from source text.
 * Used to clean up whitespace around JSX block elements.
 */
export function trimSourceLines(text: string): string {
  return text.replace(/^\n+/, "").replace(/\n+$/, "");
}
