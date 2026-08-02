/**
 * D4 — Force. RFC 2119 normative keywords -> ordinary modals.
 *
 * RFC 8174 is the whole point: a keyword carries normative weight only in ALL
 * CAPS, so a lowercase "must" is already ordinary English. Matching is therefore
 * case-SENSITIVE and whole-word — de-marking a keyword that was never marked
 * would be a no-op dressed up as a manipulation.
 *
 * Only `text` nodes are visited, so keywords inside code blocks, inline code, URLs,
 * and JSX attributes are untouched. Those are not prose and re-marking them would
 * change what the page does rather than how it reads.
 */

import type { Root, Text } from "mdast";
import { visit } from "unist-util-visit";
import { lineOf } from "../ast.js";
import { record, type Rule, type RuleContext } from "./rule.js";

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Longest keys first, so "MUST NOT" is matched before "MUST" — otherwise every
 * prohibition would silently become an obligation, which is a corrupted relation
 * introduced by the instrument rather than measured by it.
 */
export function buildKeywordPattern(keywords: Record<string, string>): RegExp {
  const alternatives = Object.keys(keywords)
    .sort((a, b) => b.length - a.length)
    .map(escapeRegExp)
    .join("|");
  return new RegExp(`\\b(${alternatives})\\b`, "g");
}

export const d4Keywords: Rule = {
  id: "D4",
  description: "ALL CAPS RFC 2119 keywords -> ordinary modals (RFC 8174)",

  apply(tree: Root, ctx: RuleContext): void {
    const keywords = ctx.templates.d4_force_keywords;
    if (Object.keys(keywords).length === 0) return;

    const pattern = buildKeywordPattern(keywords);

    visit(tree, "text", (node: Text) => {
      pattern.lastIndex = 0;
      if (!pattern.test(node.value)) return;

      pattern.lastIndex = 0;
      const seen: string[] = [];
      node.value = node.value.replace(pattern, (match) => {
        seen.push(match);
        return keywords[match] ?? match;
      });

      for (const match of seen) {
        record(ctx, "D4", `normative keyword "${match}"`, lineOf(node));
      }
    });
  },
};
