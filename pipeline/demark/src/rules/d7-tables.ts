/**
 * D7 — Precondition. GFM tables -> prose enumeration, in place.
 *
 * Cell contents are spliced in as phrasing nodes rather than flattened to plain
 * text, so inline code, links, and emphasis survive. Flattening would strip
 * formatting that carries meaning in a docs table (`--flag` becoming --flag) and
 * that loss would land only on the implicit arm.
 */

import type { PhrasingContent, Root, Table, TableRow } from "mdast";
import { lineOf, paragraph, textOf, textParagraph, type BlockNode } from "../ast.js";
import { except, record, type Rule, type RuleContext } from "./rule.js";

/**
 * Splits a template around one placeholder and inserts nodes at that position,
 * so templated wording and real phrasing content can be combined without either
 * being reduced to a string.
 */
function splice(template: string, placeholder: string, nodes: PhrasingContent[]): PhrasingContent[] {
  const marker = `{${placeholder}}`;
  const at = template.indexOf(marker);
  if (at === -1) return [{ type: "text", value: template }, ...nodes];

  const before = template.slice(0, at);
  const after = template.slice(at + marker.length);
  const out: PhrasingContent[] = [];
  if (before !== "") out.push({ type: "text", value: before });
  out.push(...nodes);
  if (after !== "") out.push({ type: "text", value: after });
  return out;
}

function rowToParagraph(
  row: TableRow,
  headers: readonly string[],
  t: RuleContext["templates"]["d7_precondition_table"],
): BlockNode {
  const cells = row.children;
  const [firstCell, ...restCells] = cells;

  const children: PhrasingContent[] = splice(
    t.row_prefix,
    "first_cell",
    (firstCell?.children ?? []) as PhrasingContent[],
  );
  children.push({ type: "text", value: " " });

  restCells.forEach((cell, index) => {
    const header = headers[index + 1] ?? "";
    const pattern = t.cell_pattern.replace(/\{header\}/g, header);
    children.push(...splice(pattern, "value", cell.children as PhrasingContent[]));
    children.push({
      type: "text",
      value: index === restCells.length - 1 ? t.row_terminator : t.cell_separator,
    });
  });

  return paragraph(children);
}

export const d7Tables: Rule = {
  id: "D7",
  description: "GFM table -> prose enumeration, one sentence per row",

  apply(tree: Root, ctx: RuleContext): void {
    const t = ctx.templates.d7_precondition_table;

    for (let i = tree.children.length - 1; i >= 0; i--) {
      const node = tree.children[i];
      if (node?.type !== "table") continue;

      const table = node as Table;
      const line = lineOf(table);
      const [headerRow, ...bodyRows] = table.children;

      if (!headerRow) {
        except(ctx, "D7", "table has no header row", line);
        continue;
      }
      if (bodyRows.length === 0) {
        except(ctx, "D7", "table has a header but no body rows", line);
        continue;
      }

      const headers = headerRow.children.map((cell) => textOf(cell).trim());
      const replacement: BlockNode[] = [textParagraph(t.lead_in)];
      for (const row of bodyRows) {
        replacement.push(rowToParagraph(row, headers, t));
      }

      tree.children.splice(i, 1, ...(replacement as never[]));
      record(ctx, "D7", `table with ${bodyRows.length} rows`, line);
    }
  },
};
