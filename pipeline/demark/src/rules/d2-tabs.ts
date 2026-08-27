/**
 * D2 — Membership. `<Tabs>` / `<TabItem>` + custom wrappers -> prose enumeration.
 *
 * The lead-in states the alternatives relation in words exactly once. This is the
 * rule where propositional equivalence is easiest to violate by accident: tabs
 * assert \"these are alternatives\" structurally, so if the prose does not assert
 * it too, the implicit arm says strictly less and any measured gap is an artifact
 * of the transform. The lead-in is not decoration — it is the relational content.
 *
 * Recognises the corpus's custom tab wrappers (PackageManagerTabs, UIFrameworkTabs,
 * AstroVueTabs, StaticSsrTabs, JavascriptFlavorTabs, AstroJSXTabs) which use
 * <Fragment slot=\"label\"> instead of <TabItem label=\"label\">.
 * These are the dominant tab idiom in the corpus (~110 English pages).
 */

import type { Root } from "mdast";
import type { MdxJsxFlowElement } from "mdast-util-mdx";
import { jsxAttr, lineOf } from "../ast.js";
import { fill } from "../templates.js";
import type { Patch } from "../types.js";
import { except, nodeSource, record, trimSourceLines, type Rule, type RuleContext } from "./rule.js";

/** Custom tab wrapper component names that replace `<Tabs>`. */
const CUSTOM_TAB_WRAPPERS = new Set([
  "PackageManagerTabs",
  "UIFrameworkTabs",
  "AstroVueTabs",
  "StaticSsrTabs",
  "JavascriptFlavorTabs",
  "AstroJSXTabs",
]);

/** True if the node is a recognized tab wrapper (including raw <Tabs>). */
function isTabWrapper(node: unknown): node is MdxJsxFlowElement {
  if (!(node as MdxJsxFlowElement | undefined)?.name) return false;
  const name = (node as MdxJsxFlowElement).name!;
  return name === "Tabs" || CUSTOM_TAB_WRAPPERS.has(name);
}

/**
 * Get the tab children from a tab wrapper.
 * Raw <Tabs> uses <TabItem>; custom wrappers use <Fragment slot="...">.
 * Returns an array of { label, node } pairs.
 */
interface TabChild {
  label: string;
  node: MdxJsxFlowElement;
  /** Whether the label is a literal (vs. an expression we cannot resolve). */
  literalLabel: boolean;
}

function getTabChildren(wrapper: MdxJsxFlowElement): TabChild[] {
  const children: TabChild[] = [];

  for (const child of wrapper.children) {
    const el = child as unknown as MdxJsxFlowElement;
    if (el.type !== "mdxJsxFlowElement") continue;

    if (el.name === "Fragment") {
      // Custom wrapper: label comes from slot attribute
      const slot = jsxAttr(el, "slot");
      if (slot === undefined) continue;
      children.push({ label: slot, node: el, literalLabel: true });
    } else if (el.name === "TabItem") {
      // Raw <TabItem>
      const label = jsxAttr(el, "label");
      if (label === undefined) {
        // Check if it's an expression attribute
        children.push({ label: "", node: el, literalLabel: false });
      } else {
        children.push({ label, node: el, literalLabel: true });
      }
    }
  }

  return children;
}

/** Extract verbatim child content from the source, stripping the wrapper tags. */
function childContent(source: string, node: MdxJsxFlowElement): string {
  const raw = nodeSource(source, node);
  if (raw === undefined) return "";
  // Strip the wrapper tags (<TabItem>...</TabItem> or <Fragment>...</Fragment>),
  // keeping only the inner content (including newlines)
  const inner = raw.replace(/^<[^>]+>\n*/, "").replace(/\n*<\/[^>]+>$/, "");
  return inner;
}

export const d2Tabs: Rule = {
  id: "D2",
  description: "Tabs/TabItem and custom wrappers -> prose enumeration with the alternatives relation stated",

  apply(source: string, tree: Root, ctx: RuleContext, patches: Patch[]): void {
    const t = ctx.templates.d2_membership;

    for (let i = tree.children.length - 1; i >= 0; i--) {
      const node = tree.children[i];
      if (!node || !isTabWrapper(node)) continue;

      const start = node.position?.start.offset;
      const end = node.position?.end.offset;
      if (start === undefined || end === undefined) {
        except(ctx, "D2", "Tab wrapper has no position offsets", lineOf(node));
        continue;
      }

      const line = lineOf(node);
      const tabs = getTabChildren(node);

      if (tabs.length === 0) {
        except(ctx, "D2", `<${node.name}> has no tab children`, line);
        continue;
      }

      // Check for non-literal labels (expression attributes)
      const unlabelled = tabs.filter((t) => !t.literalLabel);
      if (unlabelled.length > 0) {
        except(
          ctx,
          "D2",
          `${unlabelled.length} tab(s) have no literal label attribute (expression label?)`,
          line,
        );
        continue;
      }

      // Build replacement
      const parts: string[] = [t.lead_in];

      for (const tab of tabs) {
        const content = childContent(source, tab.node);
        const prefix = fill(t.option_prefix, { label: tab.label });
        parts.push(`${prefix}\n\n${trimSourceLines(content)}`);
      }

      const replacement = parts.join("\n\n");
      patches.push({
        start,
        end,
        replacement: replacement + "\n",
      });
      record(ctx, "D2", `<${node.name}> with ${tabs.length} alternatives`, line);
    }
  },
};
