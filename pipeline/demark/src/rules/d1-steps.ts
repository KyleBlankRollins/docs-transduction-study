/**
 * D1 — Sequence. `<Steps>` component -> prose, order preserved in sentence order.
 *
 * Per ADR-0002, patches the source range of `<Steps>...</Steps>` with replacement
 * text built from templates + verbatim step content from source slices.
 * Because each step's content is preserved as source text, nested containers
 * inside steps (tables, asides) get de-marked by later fixpoint passes.
 */

import type { Root } from "mdast";
import { isJsxElement, lineOf } from "../ast.js";
import { ordinal } from "../templates.js";
import type { Patch } from "../types.js";
import { except, record, trimSourceLines, type Rule, type RuleContext } from "./rule.js";

export const d1Steps: Rule = {
  id: "D1",
  description: "Steps component -> prose paragraphs with ordinal connectives",

  apply(source: string, tree: Root, ctx: RuleContext, patches: Patch[]): void {
    const t = ctx.templates.d1_sequence;

    for (let i = tree.children.length - 1; i >= 0; i--) {
      const node = tree.children[i];
      if (!node || !isJsxElement(node, "Steps")) continue;

      const start = node.position?.start.offset;
      const end = node.position?.end.offset;
      if (start === undefined || end === undefined) {
        except(ctx, "D1", "<Steps> has no position offsets", lineOf(node));
        continue;
      }

      // Find the ordered list inside <Steps>
      const lists = node.children.filter((c): c is typeof c & { type: "list" } => c.type === "list");
      if (lists.length !== 1) {
        except(ctx, "D1", `<Steps> wraps ${lists.length} lists, expected exactly 1`, lineOf(node));
        continue;
      }

      const list = lists[0]!;
      const items = list.children;
      const line = lineOf(node);

      // Build replacement from templates + verbatim step content
      const parts: string[] = [t.lead_in];

      items.forEach((item, index) => {
        // Get verbatim content of each list item from source
        const itemStart = item.position?.start.offset;
        const itemEnd = item.position?.end.offset;
        if (itemStart === undefined || itemEnd === undefined) {
          except(ctx, "D1", `Step ${index + 1} has no position offsets`, line);
          return;
        }

        const rawContent = source.slice(itemStart, itemEnd);
        const trimmed = trimSourceLines(rawContent);

        // Remove the list marker (e.g. "1. " or "1. ") from the start
        const contentBody = trimmed.replace(/^\d+\.\s*/, "");

        // Build ordinal prefix
        const ord = ordinal(t, index, items.length);

        parts.push(`${ord} ${contentBody}`);
      });

      const replacement = parts.join("\n\n");
      patches.push({
        start,
        end,
        replacement: replacement + "\n",
      });
      record(ctx, "D1", `<Steps> with ${items.length} steps`, line);
    }
  },
};
