/**
 * D7 — Precondition. GFM tables -> prose enumeration, in place.
 *
 * Cell contents are preserved as verbatim source text from source slices,
 * so inline code, links, and emphasis survive. Flattening would strip
 * formatting that carries meaning in a docs table (`--flag` becoming --flag) and
 * that loss would land only on the implicit arm.
 *
 * Per ADR-0002, patches the full table range with replacement prose.
 */

import type { Root, Table, TableRow } from "mdast";
import { lineOf, textOf } from "../ast.js";
import type { Patch } from "../types.js";
import { except, record, type Rule, type RuleContext } from "./rule.js";

/**
 * Splits a template around one placeholder and inserts verbatim source text
 * at that position, so templated wording and real content can be combined.
 */
function splice(template: string, placeholder: string, sourceText: string): string {
  const marker = `{${placeholder}}`;
  const at = template.indexOf(marker);
  if (at === -1) return template + sourceText;

  const before = template.slice(0, at);
  const after = template.slice(at + marker.length);
  return before + sourceText + after;
}

/**
 * Build the prose representation of one table row using the header names.
 * Cell content comes from the original source to preserve inline formatting.
 */
function rowToProse(
  row: TableRow,
  headers: readonly string[],
  source: string,
  t: RuleContext["templates"]["d7_precondition_table"],
): string {
  const cells = row.children;
  const [firstCell, ...restCells] = cells;

  // Get first cell content from source, stripping markdown pipe delimiters
  let firstContent = "";
  if (firstCell?.position?.start.offset && firstCell.position?.end.offset) {
    firstContent = source.slice(firstCell.position.start.offset, firstCell.position.end.offset).trim();
    firstContent = firstContent.replace(/^\| ?/, "").replace(/ ?\|$/, "").trim();
  } else if (firstCell) {
    firstContent = textOf(firstCell).trim();
  }

  let result = splice(t.row_prefix, "first_cell", firstContent);
  result += " ";

  restCells.forEach((cell, index) => {
    const header = headers[index + 1] ?? "";

    let cellContent = "";
    if (cell?.position?.start.offset && cell.position?.end.offset) {
      cellContent = source.slice(cell.position.start.offset, cell.position.end.offset).trim();
      cellContent = cellContent.replace(/^\| ?/, "").replace(/ ?\|$/, "").trim();
    } else if (cell) {
      cellContent = textOf(cell).trim();
    }

    const pattern = t.cell_pattern.replace(/\{header\}/g, header);
    result += splice(pattern, "value", cellContent);
    result += index === restCells.length - 1 ? t.row_terminator : t.cell_separator;
  });

  return result;
}

export const d7Tables: Rule = {
  id: "D7",
  description: "GFM table -> prose enumeration, one sentence per row",

  apply(source: string, tree: Root, ctx: RuleContext, patches: Patch[]): void {
    const t = ctx.templates.d7_precondition_table;

    for (let i = tree.children.length - 1; i >= 0; i--) {
      const node = tree.children[i];
      if (node?.type !== "table") continue;

      const table = node as Table;
      const start = table.position?.start.offset;
      const end = table.position?.end.offset;
      if (start === undefined || end === undefined) {
        except(ctx, "D7", "table has no position offsets", lineOf(table));
        continue;
      }

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

      const parts: string[] = [t.lead_in];
      for (const row of bodyRows) {
        parts.push(rowToProse(row, headers, source, t));
      }

      const replacement = parts.join("\n\n");
      patches.push({
        start,
        end,
        replacement: replacement + "\n",
      });
      record(ctx, "D7", `table with ${bodyRows.length} rows`, line);
    }
  },
};