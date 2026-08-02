/**
 * D2 — Membership. `<Tabs>` / `<TabItem>` -> prose enumeration.
 *
 * The lead-in states the alternatives relation in words exactly once. This is the
 * rule where propositional equivalence is easiest to violate by accident: tabs
 * assert "these are alternatives" structurally, so if the prose does not assert
 * it too, the implicit arm says strictly less and any measured gap is an artifact
 * of the transform. The lead-in is not decoration — it is the relational content.
 */

import type { Root } from "mdast";
import { ensureTerminated, isJsxElement, jsxAttr, lineOf, textParagraph, type BlockNode } from "../ast.js";
import { fill } from "../templates.js";
import { except, record, type Rule, type RuleContext } from "./rule.js";

export const d2Tabs: Rule = {
  id: "D2",
  description: "Tabs/TabItem -> prose enumeration with the alternatives relation stated",

  apply(tree: Root, ctx: RuleContext): void {
    const t = ctx.templates.d2_membership;

    for (let i = tree.children.length - 1; i >= 0; i--) {
      const node = tree.children[i];
      if (!node || !isJsxElement(node, "Tabs")) continue;

      const line = lineOf(node);
      const tabs = node.children.filter((c) => isJsxElement(c, "TabItem"));

      if (tabs.length === 0) {
        except(ctx, "D2", "<Tabs> contains no <TabItem> children", line);
        continue;
      }

      const unlabelled = tabs.filter((tab) => jsxAttr(tab, "label") === undefined);
      if (unlabelled.length > 0) {
        except(
          ctx,
          "D2",
          `${unlabelled.length} <TabItem> have no literal label attribute (expression label?)`,
          line,
        );
        continue;
      }

      const replacement: BlockNode[] = [textParagraph(t.lead_in)];

      for (const tab of tabs) {
        const label = jsxAttr(tab, "label") as string;
        replacement.push(textParagraph(fill(t.option_prefix, { label })));
        replacement.push(...ensureTerminated(tab.children as BlockNode[]));
      }

      tree.children.splice(i, 1, ...(replacement as never[]));
      record(ctx, "D2", `<Tabs> with ${tabs.length} alternatives`, line);
    }
  },
};
