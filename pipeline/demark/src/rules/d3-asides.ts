/**
 * D3 — Force. Admonitions -> inline sentences in surrounding prose, in place.
 *
 * Handles both Starlight aside spellings: the directive form (`:::caution`) and
 * the component form (`<Aside type="caution">`).
 *
 * The force phrase is mandatory, not optional. An admonition asserts "this is a
 * warning" through its type; dropping the block without restating that in words
 * removes information rather than re-encoding it, and would strawman the arm.
 */

import type { Paragraph, Root } from "mdast";
import type { ContainerDirective } from "mdast-util-directive";
import type { MdxJsxFlowElement } from "mdast-util-mdx";
import {
  ensureTerminated,
  isContainerDirective,
  isJsxElement,
  jsxAttr,
  lineOf,
  prefixParagraph,
  textOf,
  textParagraph,
  type BlockNode,
} from "../ast.js";
import { fill, type Templates } from "../templates.js";
import { except, record, type Rule, type RuleContext } from "./rule.js";

const ASIDE_TYPES = ["note", "tip", "caution", "danger"] as const;
type AsideType = (typeof ASIDE_TYPES)[number];

function isAsideType(value: string): value is AsideType {
  return (ASIDE_TYPES as readonly string[]).includes(value);
}

function forcePhrase(t: Templates["d3_force_aside"], type: string, title: string | undefined): string {
  if (title !== undefined && title.trim() !== "") return fill(t.titled, { title: title.trim() });
  return isAsideType(type) ? t[type] : t.default;
}

/** Starlight puts a custom aside title in the directive label paragraph. */
function splitDirectiveLabel(node: ContainerDirective): { title: string | undefined; body: BlockNode[] } {
  const [first, ...rest] = node.children as BlockNode[];
  if (first?.type === "paragraph" && (first.data as { directiveLabel?: boolean } | undefined)?.directiveLabel) {
    return { title: textOf(first), body: rest };
  }
  return { title: undefined, body: node.children as BlockNode[] };
}

function inlineAside(phrase: string, body: BlockNode[]): BlockNode[] {
  const [first, ...rest] = body;
  if (first?.type === "paragraph") {
    return ensureTerminated([prefixParagraph(first as Paragraph, phrase), ...rest]);
  }
  return ensureTerminated([textParagraph(phrase), ...body]);
}

export const d3Asides: Rule = {
  id: "D3",
  description: "Asides (directive and component form) -> inline prose carrying the same force",

  apply(tree: Root, ctx: RuleContext): void {
    const t = ctx.templates.d3_force_aside;

    for (let i = tree.children.length - 1; i >= 0; i--) {
      const node = tree.children[i];
      if (!node) continue;

      if (isContainerDirective(node) && isAsideType(node.name)) {
        const { title, body } = splitDirectiveLabel(node);
        if (body.length === 0) {
          except(ctx, "D3", `:::${node.name} has no body`, lineOf(node));
          continue;
        }
        tree.children.splice(i, 1, ...(inlineAside(forcePhrase(t, node.name, title), body) as never[]));
        record(ctx, "D3", `:::${node.name} directive`, lineOf(node));
        continue;
      }

      if (isJsxElement(node, "Aside")) {
        const element = node as MdxJsxFlowElement;
        const type = jsxAttr(element, "type") ?? "note";
        const title = jsxAttr(element, "title");
        const body = element.children as BlockNode[];
        if (body.length === 0) {
          except(ctx, "D3", `<Aside type="${type}"> has no body`, lineOf(node));
          continue;
        }
        tree.children.splice(i, 1, ...(inlineAside(forcePhrase(t, type, title), body) as never[]));
        record(ctx, "D3", `<Aside type="${type}">`, lineOf(node));
      }
    }
  },
};
