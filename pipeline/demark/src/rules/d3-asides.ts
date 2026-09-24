/**
 * D3 — Force. Admonitions -> inline sentences in surrounding prose, in place.
 *
 * Handles both Starlight aside spellings: the directive form (`:::caution`) and
 * the component form (`<Aside type=\"caution\">`).
 *
 * The force phrase is mandatory, not optional. An admonition asserts \"this is a
 * warning\" through its type; dropping the block without restating that in words
 * removes information rather than re-encoding it, and would strawman the arm.
 *
 * Per ADR-0002, patches the source range of the aside with replacement text
 * built from templates + verbatim aside content from source slices.
 */

import type { Root } from "mdast";
import type { ContainerDirective } from "mdast-util-directive";
import type { MdxJsxFlowElement } from "mdast-util-mdx";
import {
  isContainerDirective,
  isJsxElement,
  jsxAttr,
  lineOf,
} from "../ast.js";
import { fill, type Templates } from "../templates.js";
import type { Patch } from "../types.js";
import { except, nodeSource, record, trimSourceLines, type Rule, type RuleContext } from "./rule.js";

const ASIDE_TYPES = ["note", "tip", "caution", "danger"] as const;
type AsideType = (typeof ASIDE_TYPES)[number];

function isAsideType(value: string): value is AsideType {
  return (ASIDE_TYPES as readonly string[]).includes(value);
}

/**
 * Join the force phrase to the aside body. A body that opens with a block-level
 * HTML/JSX element (e.g. `<details>`) must start its own paragraph: written on
 * the phrase's line it becomes inline JSX that MDX rejects as unclosed
 * (amendment A5, 2026-09-23).
 */
export function joinPhrase(phrase: string, body: string): string {
  return /^<[A-Za-z]/.test(body) ? `${phrase}\n\n${body}` : `${phrase} ${body}`;
}

function forcePhrase(t: Templates["d3_force_aside"], type: string, title: string | undefined): string {
  if (title !== undefined && title.trim() !== "") return fill(t.titled, { title: title.trim() });
  return isAsideType(type) ? t[type] : t.default;
}

/** Starlight puts a custom aside title in the directive label paragraph. */
function splitDirectiveLabel(node: ContainerDirective): { title: string | undefined } {
  const children = node.children as Array<{ type: string; children?: unknown[]; data?: { directiveLabel?: boolean } }>;
  const [first] = children;
  if (first?.type === "paragraph" && first.data?.directiveLabel) {
    const textContent = first.children
      ?.map((c: unknown) => (c as { value?: string }).value ?? "")
      .join("") ?? "";
    return { title: textContent };
  }
  return { title: undefined };
}

export const d3Asides: Rule = {
  id: "D3",
  description: "Asides (directive and component form) -> inline prose carrying the same force",

  apply(source: string, tree: Root, ctx: RuleContext, patches: Patch[]): void {
    const t = ctx.templates.d3_force_aside;

    for (let i = tree.children.length - 1; i >= 0; i--) {
      const node = tree.children[i];
      if (!node) continue;

      const start = node.position?.start.offset;
      const end = node.position?.end.offset;
      if (start === undefined || end === undefined) {
        except(ctx, "D3", "Aside has no position offsets", lineOf(node));
        continue;
      }

      const line = lineOf(node);

      if (isContainerDirective(node) && isAsideType(node.name)) {
        const { title } = splitDirectiveLabel(node);
        const body = nodeSource(source, node);
        if (!body) {
          except(ctx, "D3", `:::${node.name} has no body`, line);
          continue;
        }
        // Strip the directive container markers dynamically
        const namePattern = node.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const directiveStart = new RegExp(`^:::${namePattern}\\s*(?:\\[[^\\]]*\\])?\\s*\\n?`, "i");
        const innerContent = body
          .replace(directiveStart, "")
          .replace(/\n[ \t]*:::$/, "")  // closing ::: with optional indentation
          .replace(/^[ \t]*:::[ \t]*\n?/, "");  // fallback for any remaining markers

        const phrase = forcePhrase(t, node.name, title);
        const trimmedBody = trimSourceLines(innerContent);
        const replacement = joinPhrase(phrase, trimmedBody);

        patches.push({ start, end, replacement: replacement + "\n" });
        record(ctx, "D3", `:::${node.name} directive`, line);
        continue;
      }

      if (isJsxElement(node, "Aside")) {
        const element = node as MdxJsxFlowElement;
        const type = jsxAttr(element, "type") ?? "note";
        const title = jsxAttr(element, "title");
        const body = nodeSource(source, element);
        if (!body) {
          except(ctx, "D3", `<Aside type="${type}"> has no body`, line);
          continue;
        }

        // Strip the component tags
        const innerContent = body.replace(/^<Aside[^>]*>\n?/i, "").replace(/\n?<\/Aside>$/i, "");

        const phrase = forcePhrase(t, type, title);
        const trimmedBody = trimSourceLines(innerContent);
        const replacement = joinPhrase(phrase, trimmedBody);

        patches.push({ start, end, replacement: replacement + "\n" });
        record(ctx, "D3", `<Aside type="${type}">`, line);
      }
    }
  },
};
