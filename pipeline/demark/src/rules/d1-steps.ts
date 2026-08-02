/**
 * D1 — Sequence. `<Steps>` component -> prose, order preserved in sentence order.
 *
 * Step content is not flattened into one paragraph: list items routinely contain
 * code blocks, and destroying those would be an information manipulation rather
 * than a marking one. Each step's blocks are spliced in as siblings, with the
 * ordinal connective prefixed to the step's first paragraph. That is what "order
 * preserved in sentence sequence" can mean without touching content.
 */

import type { List, ListItem, Root } from "mdast";
import { ensureTerminated, isJsxElement, lineOf, prefixParagraph, textParagraph, type BlockNode } from "../ast.js";
import { ordinal } from "../templates.js";
import { except, record, type Rule, type RuleContext } from "./rule.js";

function stepBlocks(item: ListItem, connective: string): BlockNode[] {
  const blocks = item.children as BlockNode[];
  const [first, ...rest] = blocks;
  if (first?.type === "paragraph") {
    return ensureTerminated([prefixParagraph(first, connective), ...rest]);
  }
  return ensureTerminated([textParagraph(connective.replace(/,$/, ":")), ...blocks]);
}

export const d1Steps: Rule = {
  id: "D1",
  description: "Steps component -> prose paragraphs with ordinal connectives",

  apply(tree: Root, ctx: RuleContext): void {
    const t = ctx.templates.d1_sequence;

    for (let i = tree.children.length - 1; i >= 0; i--) {
      const node = tree.children[i];
      if (!node || !isJsxElement(node, "Steps")) continue;

      const line = lineOf(node);
      const lists = node.children.filter((c): c is List => c.type === "list");

      if (lists.length !== 1) {
        except(ctx, "D1", `<Steps> wraps ${lists.length} lists, expected exactly 1`, line);
        continue;
      }

      const list = lists[0] as List;
      const items = list.children;
      const replacement: BlockNode[] = [textParagraph(t.lead_in)];

      items.forEach((item, index) => {
        replacement.push(...stepBlocks(item, ordinal(t, index, items.length)));
      });

      tree.children.splice(i, 1, ...(replacement as never[]));
      record(ctx, "D1", `<Steps> with ${items.length} steps`, line);
    }
  },
};
