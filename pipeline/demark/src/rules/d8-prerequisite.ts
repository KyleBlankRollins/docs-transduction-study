/**
 * D8 — Precondition. Prerequisite-heading blocks -> heading removed,
 * content unchanged, introduced by a template sentence.
 *
 * Added by amendment A1. Targets `##`/`###` headings whose text matches one of
 * the D8 `heading_patterns` (case-insensitive). The heading line is replaced by
 * the template's `lead_in` sentence; the body content below the heading is
 * preserved verbatim from source.
 *
 * Per ADR-0002, patches the heading range only — not the block content below it.
 * D8 operates at the heading level, not on a container that wraps the heading +
 * content, so "heading removed, content in place" means the heading is rewritten
 * to the lead-in sentence and the content bytes are untouched.
 */

import type { Heading, Root } from "mdast";
import { lineOf } from "../ast.js";
import type { Patch } from "../types.js";
import { except, record, type Rule, type RuleContext } from "./rule.js";

/** Build a single combined regex from the template's heading_patterns array. */
function buildPattern(patterns: readonly string[]): RegExp {
  // Patterns come from templates.json with explicit ^ and $ anchors.
  // Escape only regex special chars except ^ and $ (the anchors).
  const escaped = patterns.map((p) => {
    // Remove anchors if present, we'll wrap the whole thing
    let body = p.replace(/^\^/, "").replace(/\$$/, "");
    body = body.replace(/[.*+?{}()|[\]\\]/g, "\\$&");
    return body;
  });
  return new RegExp(`^(${escaped.join("|")})$`, "i");
}

export const d8Prerequisite: Rule = {
  id: "D8",
  description: "Prerequisite-heading blocks -> template sentence, content in place",

  apply(_source: string, tree: Root, ctx: RuleContext, patches: Patch[]): void {
    const t = ctx.templates.d8_prerequisite_heading;
    const headingPattern = buildPattern(t.heading_patterns);

    for (let i = tree.children.length - 1; i >= 0; i--) {
      const node = tree.children[i];
      if (!node || node.type !== "heading") continue;

      const heading = node as Heading;
      // Only target level 2 (##) and level 3 (###) headings
      if (heading.depth !== 2 && heading.depth !== 3) continue;

      const headingText = textContent(heading);
      if (!headingPattern.test(headingText.trim())) continue;

      const start = heading.position?.start.offset;
      const end = heading.position?.end.offset;
      if (start === undefined || end === undefined) {
        except(ctx, "D8", "Heading has no position offsets", lineOf(heading));
        continue;
      }

      const line = lineOf(heading);
      const replacement = t.lead_in;

      patches.push({
        start,
        end,
        replacement,
      });
      record(ctx, "D8", `heading "${headingText.trim()}" -> prerequisite lead-in`, line);
    }
  },
};

/** Extract visible text content from a heading node. */
function textContent(node: Heading): string {
  return node.children
    .map((child) => {
      if ("value" in child && typeof child.value === "string") return child.value;
      if ("children" in child && Array.isArray(child.children)) {
        return (child.children as { value?: string }[])
          .map((c) => c.value ?? "")
          .join("");
      }
      return "";
    })
    .join("");
}